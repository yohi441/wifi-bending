document.addEventListener('alpine:init', () => {
    Alpine.data('portal', () => {
        const cfg = window.portalConfig || {}
        return {
            tab: 'coin',
            amount: 0, minutes: 0, safe: false,
            buttonEnabled: false, autoGrantSeconds: 10, rate: 6,
            connecting: false, autoGrantActive: true, showTiers: false,
            voucherError: cfg.error || '', voucherLoading: false, code: '',

            init() {
                const interval = cfg.pollInterval || 2000
                this.poll()
                setInterval(() => this.poll(), interval)
            },

            async poll() {
                if (this.connecting) return
                try {
                    const r = await fetch('/coin-status'), d = await r.json()
                    this.amount = d.amount; this.minutes = d.minutes; this.safe = d.safe
                    this.buttonEnabled = d.button_enabled
                    this.autoGrantSeconds = d.auto_grant_seconds; this.rate = d.rate
                    if (d.auto_grant_seconds <= 0 && d.button_enabled && d.amount > 0 && this.autoGrantActive)
                        this.connectCoin()
                } catch(e) {}
            },

            async connectCoin() {
                if (this.connecting || this.amount < 1) return
                this.connecting = true; this.autoGrantActive = false
                try {
                    const r = await fetch('/coin-connect', {method:'POST'}), d = await r.json()
                    if (d.success) window.location.href = '/portal'
                    else { this.connecting = false; this.autoGrantActive = true; alert(d.message) }
                } catch(e) { this.connecting = false; this.autoGrantActive = true; alert('Connection error') }
            },

            formatCode() {
                let v = this.code.replace(/[^A-Za-z0-9]/g,'').toUpperCase()
                if (v.length > 8) v = v.slice(0,8)
                if (v.length > 4) v = v.slice(0,4) + '-' + v.slice(4)
                this.code = v
            },

            async redeem() {
                const c = this.code.replace('-','').trim()
                if (c.length !== 8) { this.voucherError = 'Enter a valid 8-character code'; return }
                this.voucherError = ''; this.voucherLoading = true
                try {
                    const r = await fetch('/redeem', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({code:c})})
                    const d = await r.json()
                    d.success ? window.location.href = '/portal' : this.voucherError = d.message
                } catch(e) { this.voucherError = 'Connection error. Try again.' }
                finally { this.voucherLoading = false }
            },

            get label() {
                if (this.buttonEnabled && this.amount > 0) return `Connect — ₱${this.amount} (${this.minutes} min)`
                if (this.amount > 0) return `Insert ₱${Math.max(1, 1 - this.amount)} more (min ₱1)`
                return 'Insert Coin to Start'
            },
            get pct() { return Math.min(100, (this.amount / 50) * 100) },
            get tiers() {
                return [1, 5, 10, 20, 50, 100].map(a => {
                    const m = a * this.rate, h = Math.floor(m / 60), r = m % 60
                    return {a, t: h > 0 ? `${h}h ${r}m` : `${m} min`}
                })
            }
        }
    })
})
