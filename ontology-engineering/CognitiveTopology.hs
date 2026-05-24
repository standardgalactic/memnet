-- CognitiveTopology.hs
-- Ontology as dynamic topology

module CognitiveTopology where

data TopologicalRegion = TopologicalRegion
  { regionName :: String
  , curvature  :: Double
  , connectivity :: Double
  , torsion    :: Double
  } deriving (Show)

semanticStability
  :: TopologicalRegion
  -> Double

semanticStability r =
  connectivity r
    / (1 + abs (curvature r)
         + abs (torsion r))

highlyStable
  :: TopologicalRegion
  -> Bool

highlyStable r =
  semanticStability r > 0.75
