window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, latlng, context) {
            const p = feature.properties;
            if (p.type === 'circlemarker') {
                return L.circleMarker(latlng, radius = p._radius)
            }
            if (p.type === 'circle') {
                return L.circle(latlng, radius = p._mRadius)
            }
            return L.marker(latlng);
        }
    }
});

window.dashExtensions = Object.assign({}, window.dashExtensions, {
    dashExtensionssub: {
        draw_icon: function(feature, latlng) {
            const flag = L.icon({
                iconUrl: `assets/${feature.properties.iso2}.png`,
                iconSize: [48, 48]
            });
            return L.marker(latlng, {
                icon: flag
            });
        },
    }
});

