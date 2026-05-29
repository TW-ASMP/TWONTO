from rdflib import Graph, Namespace, RDF, RDFS, OWL
import difflib

TTL_PATH = "/home/user/TWONTO/OWL/TWONTO.ttl"

TERMS = [
    "Emergency Power Management Asset",
    "Fire And Life-Safety System Component",
    "First Aid Equipment",
    "Industrial Hygiene Asset",
    "Material Handling Asset",
    "OHSA Regulated Asset",
    "PPE",
    "TSSA Regulated Asset",
    "ECA - Air Regulated Asset",
    "ECA - Sewage Regulated Asset",
    "ECA - WSER Regulated Asset",
    "DWQMS CEL Asset",
    "Component of Interlock System",
    "ladder",
    "Emergency Eyewash or Shower",
    "generator",
    "SCBA System Component",
    "spill kit",
    "blower",
    "chlorine evaporator",
    "inlet gate",
    "primary flowmeter",
    "Primary Instrumentation",
    "RW and TRW pump",
    "traveling screen",
    "E-stop",
    "electrical gloves",
    "portable gas detector",
    "pressure relief valve",
    "tie-off anchor",
    "crane",
    "fire extinguisher",
    "pressurized piping system",
    "tie-off anchor",
    "TSSA Boiler",
]

g = Graph()
g.parse(TTL_PATH, format="turtle")

# Query 1: labels on explicit owl:Class subjects
q_class = """
SELECT DISTINCT ?label
WHERE {
  ?s a owl:Class ;
     rdfs:label ?label .
}
"""

# Query 2: all rdfs:label values regardless of type (catches unlabelled-type classes)
q_all = """
SELECT DISTINCT ?label
WHERE {
  ?s rdfs:label ?label .
}
"""

class_labels = {str(row.label) for row in g.query(q_class)}
all_labels   = {str(row.label) for row in g.query(q_all)}

found   = []
missing = []

seen = set()
for term in TERMS:
    if term in seen:
        continue
    seen.add(term)

    in_class = term in class_labels
    in_all   = term in all_labels

    if in_class or in_all:
        source = "owl:Class label" if in_class else "rdfs:label (non-class subject)"
        found.append((term, source))
    else:
        # Case-insensitive near-matches from all labels
        lower_term = term.lower()
        near = [l for l in all_labels if l.lower() == lower_term]
        if not near:
            near = difflib.get_close_matches(term, all_labels, n=3, cutoff=0.6)
        missing.append((term, near))

print("=" * 70)
print(f"TWONTO.ttl — rdfs:label verification")
print(f"Total owl:Class labels in ontology : {len(class_labels)}")
print(f"Total rdfs:label values in ontology: {len(all_labels)}")
print("=" * 70)

print(f"\nFOUND ({len(found)}):")
for term, source in found:
    print(f"  ✓  {term!r}   [{source}]")

print(f"\nNOT FOUND ({len(missing)}):")
for term, near in missing:
    if near:
        print(f"  ✗  {term!r}")
        for n in near:
            print(f"       ~ near match: {n!r}")
    else:
        print(f"  ✗  {term!r}   (no near matches)")
