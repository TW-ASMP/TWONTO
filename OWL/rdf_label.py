from rdflib import *
import rdflib
import re

def rdf_label(input_filename, output_filename):
    g = Graph()
    g2 = Graph()
    g.parse(input_filename, format="turtle")

    qres = g.query("""SELECT ?subject ?label

    WHERE { 
    ?subject rdfs:label ?label 

    } LIMIT 100""")


    print(qres)

    for i in g:
        hasLiteral = False
        for j in i:
            if type(j) == rdflib.term.Literal:
                hasLiteral = True
        if not hasLiteral:
            l = i[0].split('#')[-1]
            lit = re.sub('([A-Z][a-z]+)', r' \1', re.sub('([A-Z]+)', r' \1', l)).split()
            label = " ".join(lit)
            k = (*i, rdflib.term.Literal(label))
            print(k)
            if len(k) < 3:
                g2.add(k)
        else:
            g2.add(i)

    g2.serialize(output_filename, format="turtle")


if __name__ == "__main__":
    rdf_label("FAMO.owl","FAMO.ttl")