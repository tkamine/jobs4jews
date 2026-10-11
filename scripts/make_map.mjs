// Projects US state outlines and every community's lat/lon to SVG coordinates.
// Output: data/map.json  (run automatically by build.py)
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { geoAlbersUsa, geoPath } from "d3-geo";
import { feature, mesh } from "topojson-client";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(import.meta.url);
const topo = require("us-atlas/states-10m.json");

const W = 975, H = 610;
const states = feature(topo, topo.objects.states);
const projection = geoAlbersUsa().fitSize([W, H], states);
const gp = geoPath(projection).digits(1);

const dir = path.join(root, "data", "communities");
const points = fs.readdirSync(dir).filter(f => f.endsWith(".json")).map(f => {
  const c = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
  const xy = projection([c.lon, c.lat]);
  return xy ? { slug: c.slug, name: c.name, x: +xy[0].toFixed(1), y: +xy[1].toFixed(1) } : null;
}).filter(Boolean);

fs.writeFileSync(path.join(root, "data", "map.json"), JSON.stringify({
  width: W, height: H,
  states: gp(states),
  borders: gp(mesh(topo, topo.objects.states, (a, b) => a !== b)),
  points,
}));
console.log(`map.json: ${points.length} community point(s)`);
