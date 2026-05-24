-- SemanticField.hs
-- Distributed field cognition

module SemanticField where

data FieldCell = FieldCell
  { semanticDensity :: Double
  , entropy         :: Double
  , salience        :: Double
  } deriving (Show)

fieldPotential :: FieldCell -> Double
fieldPotential c =
  (semanticDensity c * salience c)
    / (1 + entropy c)

stableField :: FieldCell -> Bool
stableField c =
  fieldPotential c > 0.25

mergeFields
  :: FieldCell
  -> FieldCell
  -> FieldCell

mergeFields a b =
  FieldCell
    { semanticDensity =
        (semanticDensity a +
         semanticDensity b) / 2

    , entropy =
        (entropy a +
         entropy b) / 2

    , salience =
        max (salience a)
            (salience b)
    }
