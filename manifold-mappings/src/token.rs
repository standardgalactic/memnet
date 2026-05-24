// src/token.rs
//
// MML Lexer: converts raw source text into a flat token stream.
//
// MML token grammar (informal):
//   keyword   ::= '@manifold' | 'region' | 'flow' | 'constraint'
//               | 'mapping' | 'bubble' | 'relation' | 'residual'
//   ident     ::= [a-zA-Z_][a-zA-Z0-9_-]*
//   number    ::= [-]?[0-9]+(\.[0-9]+)?
//   string    ::= '"' [^"]* '"'
//   colon     ::= ':'
//   lbrace    ::= '{'
//   rbrace    ::= '}'
//   lbracket  ::= '['
//   rbracket  ::= ']'
//   comment   ::= '#' ... '\n'
//   whitespace (skipped)

#[derive(Debug, Clone, PartialEq)]
pub enum Token {
    // Block keywords
    At(String),      // @manifold, @include, etc.
    Keyword(String), // region, flow, constraint, mapping, bubble, relation, residual
    Ident(String),   // any bare identifier or hyphenated-name
    // Values
    Number(f64),
    StringLit(String),
    Bool(bool),
    // Punctuation
    Colon,
    LBrace,
    RBrace,
    LBracket,
    RBracket,
    // Structural
    Eof,
}

impl Token {
    pub fn is_value(&self) -> bool {
        matches!(self, Token::Number(_) | Token::StringLit(_) | Token::Bool(_) | Token::Ident(_))
    }
}

impl std::fmt::Display for Token {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Token::At(s)         => write!(f, "@{s}"),
            Token::Keyword(s)    => write!(f, "{s}"),
            Token::Ident(s)      => write!(f, "{s}"),
            Token::Number(n)     => write!(f, "{n}"),
            Token::StringLit(s)  => write!(f, "\"{s}\""),
            Token::Bool(b)       => write!(f, "{b}"),
            Token::Colon         => write!(f, ":"),
            Token::LBrace        => write!(f, "{{"),
            Token::RBrace        => write!(f, "}}"),
            Token::LBracket      => write!(f, "["),
            Token::RBracket      => write!(f, "]"),
            Token::Eof           => write!(f, "<EOF>"),
        }
    }
}

// ── Keywords ────────────────────────────────────────────────────────────────

const BLOCK_KEYWORDS: &[&str] = &[
    "region", "flow", "constraint", "mapping",
    "bubble", "relation", "residual", "include",
];

// ── Lexer ───────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct Span {
    pub line: usize,
    pub col:  usize,
}

impl std::fmt::Display for Span {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}:{}", self.line, self.col)
    }
}

#[derive(Debug, Clone)]
pub struct SpannedToken {
    pub token: Token,
    pub span:  Span,
}

pub struct Lexer<'a> {
    src:  &'a str,
    pos:  usize,
    line: usize,
    col:  usize,
}

impl<'a> Lexer<'a> {
    pub fn new(src: &'a str) -> Self {
        Self { src, pos: 0, line: 1, col: 1 }
    }

    fn peek(&self) -> Option<char> {
        self.src[self.pos..].chars().next()
    }

    fn advance(&mut self) -> Option<char> {
        let c = self.peek()?;
        self.pos += c.len_utf8();
        if c == '\n' { self.line += 1; self.col = 1; }
        else          { self.col  += 1; }
        Some(c)
    }

    fn skip_whitespace_and_comments(&mut self) {
        loop {
            match self.peek() {
                Some(c) if c.is_ascii_whitespace() => { self.advance(); }
                Some('#') => { while self.peek().map(|c| c != '\n').unwrap_or(false) { self.advance(); } }
                _ => break,
            }
        }
    }

    fn span(&self) -> Span { Span { line: self.line, col: self.col } }

    fn read_ident_or_keyword(&mut self) -> Token {
        let mut s = String::new();
        while let Some(c) = self.peek() {
            if c.is_alphanumeric() || c == '_' || c == '-' { s.push(c); self.advance(); }
            else { break; }
        }
        match s.as_str() {
            "true"  => Token::Bool(true),
            "false" => Token::Bool(false),
            k if BLOCK_KEYWORDS.contains(&k) => Token::Keyword(s),
            _ => Token::Ident(s),
        }
    }

    fn read_number(&mut self, first: char) -> Token {
        let mut s = first.to_string();
        while let Some(c) = self.peek() {
            if c.is_ascii_digit() || c == '.' { s.push(c); self.advance(); }
            else { break; }
        }
        Token::Number(s.parse().unwrap_or(0.0))
    }

    fn read_string(&mut self) -> Token {
        let mut s = String::new();
        while let Some(c) = self.advance() {
            if c == '"' { break; }
            s.push(c);
        }
        Token::StringLit(s)
    }

    pub fn tokenize(&mut self) -> Result<Vec<SpannedToken>, LexError> {
        let mut tokens = Vec::new();
        loop {
            self.skip_whitespace_and_comments();
            let span = self.span();
            let tok = match self.peek() {
                None      => { tokens.push(SpannedToken { token: Token::Eof, span }); break; }
                Some('@') => {
                    self.advance();
                    let Token::Ident(s) | Token::Keyword(s) = self.read_ident_or_keyword()
                    else { return Err(LexError { msg: "expected identifier after @".into(), span }); };
                    Token::At(s)
                }
                Some(c) if c.is_alphabetic() || c == '_' => {
                    self.advance();
                    let rest = self.read_ident_or_keyword();
                    // prepend first char
                    match rest {
                        Token::Ident(mut s)   => { s.insert(0, c); Token::Ident(s) }
                        Token::Keyword(mut s) => { s.insert(0, c); Token::Keyword(s) }
                        Token::Bool(b)        => Token::Bool(b),
                        other                 => other,
                    }
                }
                Some(c) if c.is_ascii_digit() => { self.advance(); self.read_number(c) }
                Some('-') => {
                    self.advance();
                    if self.peek().map(|c| c.is_ascii_digit()).unwrap_or(false) {
                        let d = self.advance().unwrap();
                        match self.read_number(d) {
                            Token::Number(n) => Token::Number(-n),
                            t => t,
                        }
                    } else {
                        // hyphen in identifier — backtrack not possible; treat as ident start
                        Token::Ident("-".into())
                    }
                }
                Some('"') => { self.advance(); self.read_string() }
                Some(':') => { self.advance(); Token::Colon }
                Some('{') => { self.advance(); Token::LBrace }
                Some('}') => { self.advance(); Token::RBrace }
                Some('[') => { self.advance(); Token::LBracket }
                Some(']') => { self.advance(); Token::RBracket }
                Some(c)   => {
                    return Err(LexError { msg: format!("unexpected character '{c}'"), span });
                }
            };
            tokens.push(SpannedToken { token: tok, span });
        }
        Ok(tokens)
    }
}

#[derive(Debug, Clone)]
pub struct LexError {
    pub msg:  String,
    pub span: Span,
}

impl std::fmt::Display for LexError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "LexError at {}: {}", self.span, self.msg)
    }
}

// ── Tests ───────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn lex(src: &str) -> Vec<Token> {
        Lexer::new(src).tokenize().unwrap().into_iter().map(|st| st.token).collect()
    }

    #[test]
    fn lex_at_keyword() {
        let t = lex("@manifold");
        assert_eq!(t[0], Token::At("manifold".into()));
    }

    #[test]
    fn lex_number_negative() {
        let t = lex("-0.42");
        assert_eq!(t[0], Token::Number(-0.42));
    }

    #[test]
    fn lex_block() {
        let t = lex("region foo { entropy: 0.1 }");
        assert_eq!(t[0], Token::Keyword("region".into()));
        assert_eq!(t[1], Token::Ident("foo".into()));
        assert_eq!(t[2], Token::LBrace);
    }

    #[test]
    fn lex_comment_skipped() {
        let t = lex("# comment\nregion");
        assert_eq!(t[0], Token::Keyword("region".into()));
    }

    #[test]
    fn lex_string() {
        let t = lex("\"hello world\"");
        assert_eq!(t[0], Token::StringLit("hello world".into()));
    }
}
