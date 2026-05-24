-- WaveGraph.hs
-- Interference-based semantic propagation

module WaveGraph where

import qualified Data.Map as M

type Node = String
type Weight = Double

data WaveState = WaveState
  { amplitude :: Double
  , neighbors :: [(Node, Weight)]
  } deriving (Show)

type Graph = M.Map Node WaveState

propagate :: Graph -> Node -> Double
propagate graph node =
  case M.lookup node graph of
    Nothing -> 0

    Just ws ->
      let local = amplitude ws

          neighborEnergy =
            sum
              [ w
              | (_, w) <- neighbors ws
              ]

      in (local + neighborEnergy) / 2
