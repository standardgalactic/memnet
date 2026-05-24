-- OntologicalCompression.hs
-- Semantic persistence and decay

module OntologicalCompression where

data Memory = Memory
  { label            :: String
  , age              :: Double
  , emotionalWeight  :: Double
  , accessFrequency  :: Double
  } deriving (Show)

strength :: Double -> Memory -> Double
strength halfLife m =
  let decay =
        exp (- age m / halfLife)

      emotional =
        1 + emotionalWeight m

      access =
        1 + accessFrequency m

  in decay * emotional * access

archiveCandidates
  :: Double
  -> [Memory]
  -> [Memory]

archiveCandidates h =
  filter (\m -> strength h m < 0.05)
