"""Exporta a malha (segmentos não direcionados) para o painel: data/aracaju/roads.json."""
import json
import numpy as np
z = np.load("data/aracaju/aracaju_drive.npz")
u, v = z["u"], z["v"]
a, b = np.minimum(u, v), np.maximum(u, v)
pairs = np.unique(np.stack([a, b], 1), axis=0)
lat, lon = z["lat"], z["lon"]
seg = np.column_stack([lat[pairs[:, 0]], lon[pairs[:, 0]], lat[pairs[:, 1]], lon[pairs[:, 1]]]).round(5)
bnd = json.load(open("data/aracaju/aracaju_drive.boundary.geojson"))
json.dump({"segments": seg.ravel().tolist(), "boundary": bnd,
           "attribution": "© colaboradores do OpenStreetMap (ODbL)"}, open("data/aracaju/roads.json", "w"))
print(len(pairs), "segmentos")
