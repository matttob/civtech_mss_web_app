window.dashExtensions = Object.assign({}, window.dashExtensions, {
    dashExtensionssub: {
        draw_icon: function(feature, latlng) {
            const flag = L.icon({
                iconUrl: `assets/${feature.properties.iso2}.png`,
                iconSize: [feature.properties.marker_size, feature.properties.marker_size]
            });
            return L.marker(latlng, {
                icon: flag
            });
        },
    }
});

