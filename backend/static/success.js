document.addEventListener('alpine:init', () => {
    Alpine.data('success', () => {
        const cfg = window.successConfig || {}
        return {
            remaining: cfg.remaining || 0,
            mac: cfg.mac || '',
            init() {
                setInterval(() => { if (this.remaining > 0) this.remaining-- }, 1000)
                setInterval(async () => {
                    try {
                        const r = await fetch('/status'), d = await r.json()
                        if (!d.authenticated) window.location.href = '/portal'
                    } catch(e) {}
                }, 10000)
            },
            get mins() { return Math.floor(this.remaining / 60) },
            get secs() { return this.remaining % 60 },
            get display() { return `${this.mins}:${String(this.secs).padStart(2, '0')}` }
        }
    })
})
