-- OntologyCore.hs
-- Ontology Engineering Framework
-- Constraint-first semantic structures

module OntologyCore where

type EntityId = String
type Relation  = String
type Weight    = Double

data Entity = Entity
  { entityId   :: EntityId
  , attributes :: [Attribute]
  } deriving (Show, Eq)

data Attribute = Attribute
  { key   :: String
  , value :: String
  } deriving (Show, Eq)

data SemanticEdge = SemanticEdge
  { source   :: EntityId
  , target   :: EntityId
  , relation :: Relation
  , strength :: Weight
  } deriving (Show, Eq)

data Ontology = Ontology
  { entities :: [Entity]
  , edges    :: [SemanticEdge]
  } deriving (Show)

neighbors :: Ontology -> EntityId -> [SemanticEdge]
neighbors onto eid =
  filter (\e -> source e == eid || target e == eid)
         (edges onto)

coherenceScore :: Ontology -> EntityId -> Double
coherenceScore onto eid =
  let ns = neighbors onto eid
      total = sum (map strength ns)
  in total / (1 + fromIntegral (length ns))
