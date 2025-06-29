chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'checkCompanyReviews') {
        checkCompanyReviews(request.oid)
            .then(result => {
                sendResponse({ success: true, data: result })
            })
            .catch(error => {
                console.error('[AF2GIS Background] API error:', error)
                sendResponse({ success: false, error: error.message })
            })

        return true
    }
})

async function checkCompanyReviews(oid) {
    try {
        const response = await fetch(
            `https://af2gis.ru/api/0.1/report/2gis/${oid}`
        )

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const data = await response.json()
        return data
    } catch (error) {
        console.error('[AF2GIS Background] Fetch error:', error)
        throw error
    }
}
