-- AdmissibilityEngine.hs
-- Constraint geometry for ontology evolution

module AdmissibilityEngine where

data Trajectory = Trajectory
  { energy      :: Double
  , coherence   :: Double
  , persistence :: Double
  } deriving (Show)

admissibility :: Trajectory -> Double
admissibility t =
  (coherence t * persistence t)
    / (1 + energy t)

stable :: Trajectory -> Bool
stable t =
  admissibility t > 0.5

collapse :: Trajectory -> Bool
collapse t =
  energy t > coherence t * 10
