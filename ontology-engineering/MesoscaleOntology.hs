-- MesoscaleOntology.hs
-- Structural emergence at intermediate scales

module MesoscaleOntology where

data Cluster = Cluster
  { clusterName :: String
  , microNoise  :: Double
  , macroRigidity :: Double
  , localVariance :: Double
  } deriving (Show)

coherence :: Cluster -> Double
coherence c =
  1 / (1 + localVariance c)

mesoscaleStable :: Cluster -> Bool
mesoscaleStable c =
  microNoise c < 10
  &&
  macroRigidity c < 10
  &&
  coherence c > 0.1

detectEmergence :: [Cluster] -> [Cluster]
detectEmergence =
  filter mesoscaleStable
