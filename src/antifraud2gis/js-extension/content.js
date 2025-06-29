;(function () {
    if (document.getElementById('af2gis-checker')) return

    const templates = {}

    const extractOID = () => {
        const match =
            location.href.match(/firm\/(\d+)/) ||
            location.href.match(/\/(\d{17,20})/)
        return match ? match[1] : null
    }

    const isCompanyPage = () =>
        location.href.includes('firm/') || location.href.includes('company/')

    const checkCompanyReviews = oid =>
        new Promise((resolve, reject) => {
            chrome.runtime.sendMessage(
                { action: 'checkCompanyReviews', oid },
                response => {
                    if (chrome.runtime.lastError)
                        reject(new Error(chrome.runtime.lastError.message))
                    else if (response.success) resolve(response.data)
                    else
                        reject(
                            new Error(response.error || 'Неизвестная ошибка')
                        )
                }
            )
        })

    const loadTemplate = async name => {
        if (templates[name]) return templates[name]
        const url = chrome.runtime.getURL(`templates/${name}.html`)
        const response = await fetch(url)
        templates[name] = await response.text()
        return templates[name]
    }

    const createElement = (tag, id, className) => {
        const el = document.createElement(tag)
        if (id) el.id = id
        if (className) el.className = className
        return el
    }

    const createButton = () => {
        const btn = createElement('button', 'af2gis-checker')
        btn.innerHTML = '🔍 Проверить отзывы?'
        return btn
    }

    const createWidget = () => createElement('div', 'af2gis-results')

    const renderTemplate = (template, data = {}) => {
        return template.replace(
            /\{\{(\w+)\}\}/g,
            (match, key) => data[key] || ''
        )
    }

    const showLoading = async widget => {
        widget.innerHTML = await loadTemplate('loading')
    }

    const showResults = async (widget, data, oid) => {
        let template,
            templateData = { oid }

        if (data.status === 'OK') {
            template = await loadTemplate('ok-result')
            templateData = {
                ...templateData,
                icon: data.trusted ? '🟢' : '🔴',
                text: data.trusted ? 'Отзывы надежные' : 'Отзывы ненадежные',
                statusClass: data.trusted
                    ? 'af2gis-trusted'
                    : 'af2gis-untrusted'
            }
        } else if (data.status === 'MISS') {
            template = await loadTemplate('miss-result')
        } else {
            template = await loadTemplate('no-result')
        }

        widget.innerHTML = renderTemplate(template, templateData)
        attachEventHandlers(widget, data)
    }

    const showError = async (widget, message) => {
        const template = await loadTemplate('error')
        widget.innerHTML = renderTemplate(template, { message })
        attachEventHandlers(widget)
    }

    const attachEventHandlers = (widget, data = {}) => {
        const checkBtn = widget.querySelector('#af2gis-check-btn')
        const closeBtn = widget.querySelector('#af2gis-close-btn')

        if (checkBtn && data.url) {
            checkBtn.onclick = () => window.open(data.url, '_blank')
        }

        if (closeBtn) {
            closeBtn.onclick = () => {
                widget.remove()
                showCheckButton()
            }
        }
    }

    const showCheckButton = () => {
        document
            .querySelectorAll('#af2gis-checker, #af2gis-results')
            .forEach(el => el.remove())

        if (!isCompanyPage()) return

        const oid = extractOID()
        if (!oid) return

        const button = createButton()
        document.body.appendChild(button)

        button.onclick = async () => {
            button.remove()
            const widget = createWidget()
            document.body.appendChild(widget)

            await showLoading(widget)

            try {
                const result = await checkCompanyReviews(oid)
                await showResults(widget, result, oid)
            } catch (error) {
                await showError(widget, 'Не удалось связаться с сервером')
            }
        }
    }

    const initChecker = () => {
        if (isCompanyPage()) {
            setTimeout(showCheckButton, 500)
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initChecker)
    } else {
        initChecker()
    }

    let currentUrl = location.href
    new MutationObserver(() => {
        if (currentUrl !== location.href) {
            currentUrl = location.href
            setTimeout(initChecker, 1000)
        }
    }).observe(document.body, { childList: true, subtree: true })
})()
