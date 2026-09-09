// compare.js — the MapLibre layer for /compare (Phase 6, UI-02).
//
// Loaded as `<script type="module">`. Reads the server-rendered GeoJSON
// block and builds a data-driven marker layer on top of it. Guards on
// `#map` being present and on the MapLibre import succeeding — a failed
// CDN load or a missing container leaves the server-rendered page fully
// usable; no figure on this page exists only inside this script.
//
// Vocabulary discipline: this file is covered by the D-70 gate over
// app/static/ — every string and comment here avoids prescriptive
// language ("recommend", "should", "best", "optimal", etc.).

const MAP_CONTAINER_ID = "map";
const GEOJSON_SCRIPT_ID = "compare-geojson";
// The default falls back to the same OpenFreeMap style URL the server
// also renders as the map container's own `data-style-url` attribute
// (compare.html) — read from the DOM first so the server-declared config
// is the single source of truth; this constant only covers the
// no-container-yet code path, which never reaches buildMap() at all.
const DEFAULT_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";
const MAPLIBRE_MODULE_URL =
  "https://cdn.jsdelivr.net/npm/maplibre-gl@6.5.0/dist/maplibre-gl.mjs";

const RANKED_LAYER_ID = "compare-cities-ranked";
const UNRANKED_LAYER_ID = "compare-cities-unranked";

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

function readGeoJson() {
  const script = document.getElementById(GEOJSON_SCRIPT_ID);
  if (!script) {
    return null;
  }
  try {
    return JSON.parse(script.textContent);
  } catch (error) {
    console.error("compare.js: could not parse the embedded GeoJSON block", error);
    return null;
  }
}

function buildMap(maplibregl, featureCollection) {
  const netRankedValues = featureCollection.features
    .filter((feature) => feature.properties.band === "net_ranked")
    .map((feature) => feature.properties.total_value);
  const minValue = netRankedValues.length ? Math.min(...netRankedValues) : 0;
  const maxValue = netRankedValues.length ? Math.max(...netRankedValues) : 1;
  // interpolate() requires a strictly increasing stop sequence — a single
  // ranked city (min === max) would otherwise raise at style-load time.
  const highStop = maxValue > minValue ? maxValue : minValue + 1;

  const container = document.getElementById(MAP_CONTAINER_ID);
  const styleUrl = (container && container.dataset.styleUrl) || DEFAULT_STYLE_URL;

  const map = new maplibregl.Map({
    container: MAP_CONTAINER_ID,
    style: styleUrl,
    center: [-40, 40],
    zoom: 1.4,
  });

  map.addControl(new maplibregl.NavigationControl(), "top-right");

  map.on("load", () => {
    map.addSource("compare-cities", {
      type: "geojson",
      data: featureCollection,
    });

    map.addLayer({
      id: RANKED_LAYER_ID,
      type: "circle",
      source: "compare-cities",
      filter: ["==", ["get", "band"], "net_ranked"],
      paint: {
        "circle-radius": 15,
        "circle-color": [
          "interpolate",
          ["linear"],
          ["get", "total_value"],
          minValue, "#2a6f97",
          highStop, "#a4133c",
        ],
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });

    map.addLayer({
      id: UNRANKED_LAYER_ID,
      type: "circle",
      source: "compare-cities",
      filter: ["==", ["get", "band"], "incentive_not_modelled"],
      paint: {
        "circle-radius": 11,
        "circle-color": "#9a9488",
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });

    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
    const bandLabel = {
      net_ranked: "ranked on net landed cost",
      incentive_not_modelled: "no incentive modelled",
    };

    for (const layerId of [RANKED_LAYER_ID, UNRANKED_LAYER_ID]) {
      map.on("mouseenter", layerId, (event) => {
        map.getCanvas().style.cursor = "pointer";
        const feature = event.features[0];
        const props = feature.properties;
        const html =
          `<strong>${escapeHtml(props.label)}</strong><br>` +
          `${escapeHtml(bandLabel[props.band] || props.band)}<br>` +
          `${escapeHtml(props.total_text)}`;
        popup.setLngLat(feature.geometry.coordinates).setHTML(html).addTo(map);
      });
      map.on("mouseleave", layerId, () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });
    }

    if (featureCollection.features.length) {
      const bounds = new maplibregl.LngLatBounds();
      for (const feature of featureCollection.features) {
        bounds.extend(feature.geometry.coordinates);
      }
      map.fitBounds(bounds, { padding: 60, maxZoom: 5 });
    }
  });
}

async function main() {
  const container = document.getElementById(MAP_CONTAINER_ID);
  if (!container) {
    return;
  }

  const featureCollection = readGeoJson();
  if (!featureCollection || !Array.isArray(featureCollection.features)) {
    return;
  }

  let maplibregl;
  try {
    maplibregl = await import(MAPLIBRE_MODULE_URL);
  } catch (error) {
    console.error(
      "compare.js: MapLibre did not load from the CDN — the ranked list " +
        "below is the full, server-rendered result and is unaffected",
      error
    );
    return;
  }

  if (!maplibregl || typeof maplibregl.Map !== "function") {
    return;
  }

  buildMap(maplibregl, featureCollection);
}

main();
