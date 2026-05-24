-- ResonanceOntology.hs
-- MEM|8-style semantic resonance

module ResonanceOntology where

import Data.List

data ResonanceNode = ResonanceNode
  { nodeName   :: String
  , frequency  :: Double
  , phase      :: Double
  , amplitude  :: Double
  } deriving (Show)

resonance :: ResonanceNode -> ResonanceNode -> Double
resonance a b =
  let freqDiff  = abs (frequency a - frequency b)
      phaseDiff = abs (phase a - phase b)
  in (amplitude a * amplitude b)
       / (1 + freqDiff + phaseDiff)

mostResonant
  :: ResonanceNode
  -> [ResonanceNode]
  -> [(String, Double)]

mostResonant query nodes =
  sortBy (\(_,a) (_,b) -> compare b a)
    [ (nodeName n, resonance query n)
    | n <- nodes
    ]
