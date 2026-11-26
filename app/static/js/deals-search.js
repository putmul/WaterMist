(function () {
    const config = window.watermistSemanticSearch;
    const target = document.getElementById("semantic-results");

    if (!config || !config.has_semantic_query || !target) {
        return;
    }

    const params = new URLSearchParams();
    Object.entries(config.params || {}).forEach(function ([key, value]) {
        if (value !== null && value !== undefined && value !== "") {
            params.set(key, value);
        }
    });

    fetch(config.url + "?" + params.toString(), {
        headers: { Accept: "text/html" },
    })
        .then(function (response) {
            if (!response.ok) {
                throw new Error("Semantic search request failed");
            }
            return response.text();
        })
        .then(function (html) {
            target.innerHTML = html;
        })
        .catch(function () {
            const literalCount = Number((config.params || {}).literal_count || 0);
            target.innerHTML =
                '<div class="empty-state semantic-message"><p>' +
                (literalCount > 0
                    ? 'Rekomendasi berdasarkan makna belum dapat dimuat. Hasil berdasarkan nama tetap tersedia.'
                    : 'Pencarian berdasarkan makna belum dapat dimuat. Coba ubah deskripsi pencarian Anda.') +
                '</p></div>';
        });
})();
