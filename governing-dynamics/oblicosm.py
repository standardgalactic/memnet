# oblicosm.py
# Oblicosm: a Spherepop + lambda-calculus language
# Interpreter plus compiler-to-Python scaffold.

import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class Bubble:
    density: float
    entropy: float
    curvature: float
    salience: float

    def admissibility(self) -> float:
        return (self.density * self.salience) / (
            1.0 + self.entropy + abs(self.curvature)
        )

    def step(self, dt: float = 0.1) -> "Bubble":
        k = self.admissibility()
        return Bubble(
            density=self.density + dt * k,
            entropy=max(0.0, self.entropy * (1.0 - dt * k)),
            curvature=self.curvature * (1.0 - 0.25 * dt * k),
            salience=self.salience + 0.5 * dt * k,
        )


class Env(dict):
    def extend(self, name: str, value: Any) -> "Env":
        e = Env(self)
        e[name] = value
        return e


@dataclass
class Lambda:
    param: str
    body: Any
    env: Env

    def __call__(self, arg):
        return eval_expr(self.body, self.env.extend(self.param, arg))


def tokenize(src: str) -> List[str]:
    return re.findall(r'\(|\)|λ|\\|[A-Za-z_][A-Za-z0-9_]*|-?\d+\.\d+|-?\d+|:=|[^\s()]', src)


def parse(tokens: List[str]):
    if not tokens:
        raise SyntaxError("unexpected EOF")

    tok = tokens.pop(0)

    if tok == "(":
        xs = []
        while tokens[0] != ")":
            xs.append(parse(tokens))
        tokens.pop(0)
        return xs

    if tok == ")":
        raise SyntaxError("unexpected )")

    if re.match(r"-?\d+\.\d+$", tok):
        return float(tok)

    if re.match(r"-?\d+$", tok):
        return int(tok)

    return tok


def parse_program(src: str):
    tokens = tokenize(src)
    forms = []
    while tokens:
        forms.append(parse(tokens))
    return forms


def eval_expr(x, env: Env):
    if isinstance(x, (int, float, Bubble)):
        return x

    if isinstance(x, str):
        return env[x]

    if not x:
        return None

    head = x[0]

    if head in ("λ", "\\"):
        _, param, body = x
        return Lambda(param, body, env)

    if head == "let":
        _, name, value = x
        env[name] = eval_expr(value, env)
        return env[name]

    if head == "bubble":
        _, d, e, c, s = x
        return Bubble(
            float(eval_expr(d, env)),
            float(eval_expr(e, env)),
            float(eval_expr(c, env)),
            float(eval_expr(s, env)),
        )

    if head == "admit":
        return eval_expr(x[1], env).admissibility()

    if head == "step":
        return eval_expr(x[1], env).step()

    if head == "print":
        val = eval_expr(x[1], env)
        print(val)
        return val

    fn = eval_expr(head, env)
    args = [eval_expr(a, env) for a in x[1:]]

    if callable(fn):
        result = fn
        for a in args:
            result = result(a)
        return result

    raise TypeError(f"not callable: {fn}")


def base_env() -> Env:
    env = Env()

    env["+"] = lambda a: lambda b: a + b
    env["-"] = lambda a: lambda b: a - b
    env["*"] = lambda a: lambda b: a * b
    env["/"] = lambda a: lambda b: a / b

    env["density"] = lambda b: b.density
    env["entropy"] = lambda b: b.entropy
    env["curvature"] = lambda b: b.curvature
    env["salience"] = lambda b: b.salience

    return env


def run(src: str):
    env = base_env()
    result = None
    for form in parse_program(src):
        result = eval_expr(form, env)
    return result


def compile_expr(x) -> str:
    if isinstance(x, (int, float)):
        return repr(x)

    if isinstance(x, str):
        return x

    head = x[0]

    if head in ("λ", "\\"):
        _, param, body = x
        return f"(lambda {param}: {compile_expr(body)})"

    if head == "bubble":
        _, d, e, c, s = x
        return f"Bubble({compile_expr(d)}, {compile_expr(e)}, {compile_expr(c)}, {compile_expr(s)})"

    if head == "admit":
        return f"{compile_expr(x[1])}.admissibility()"

    if head == "step":
        return f"{compile_expr(x[1])}.step()"

    if head == "print":
        return f"print({compile_expr(x[1])})"

    if head in ["+", "-", "*", "/"]:
        return f"({compile_expr(x[1])} {head} {compile_expr(x[2])})"

    return f"{compile_expr(head)}({', '.join(compile_expr(a) for a in x[1:])})"


def compile_program(src: str) -> str:
    out = [
        "from oblicosm import Bubble",
        "",
    ]

    for form in parse_program(src):
        if isinstance(form, list) and form[0] == "let":
            _, name, value = form
            out.append(f"{name} = {compile_expr(value)}")
        else:
            out.append(compile_expr(form))

    return "\n".join(out)


if __name__ == "__main__":
    mode = sys.argv[1]
    path = sys.argv[2]

    src = open(path, "r", encoding="utf-8").read()

    if mode == "run":
        run(src)

    elif mode == "compile":
        print(compile_program(src))

    else:
        raise SystemExit("usage: python oblicosm.py run|compile file.obl")
