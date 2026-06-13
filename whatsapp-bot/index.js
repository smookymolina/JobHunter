'use strict'

const express   = require('express')
const { Client, LocalAuth } = require('whatsapp-web.js')
const qrcode    = require('qrcode-terminal')

const app = express()
app.use(express.json())

// ── WhatsApp client ────────────────────────────────────────────────────────────

const client = new Client({
  authStrategy: new LocalAuth(),
  puppeteer: {
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--no-first-run',
      '--no-zygote',
    ],
  },
})

let isReady = false

client.on('qr', (qr) => {
  console.log('\n📱  Escanea este QR con WhatsApp (Ajustes → Dispositivos vinculados → Vincular dispositivo):')
  qrcode.generate(qr, { small: true })
})

client.on('ready', () => {
  isReady = true
  console.log('✅  WhatsApp Bot está LISTO y vinculado')
})

client.on('auth_failure', (msg) => {
  isReady = false
  console.error('❌  Fallo de autenticación WhatsApp:', msg)
})

client.on('disconnected', (reason) => {
  isReady = false
  console.warn('⚠️   WhatsApp desconectado:', reason)
})

client.initialize()

// ── HTTP endpoints ─────────────────────────────────────────────────────────────

app.get('/health', (_req, res) => {
  res.json({ ok: true, ready: isReady })
})

app.post('/send', async (req, res) => {
  const { phone, message } = req.body

  if (!phone || !message) {
    return res.status(400).json({ ok: false, error: 'phone y message son requeridos' })
  }

  if (!isReady) {
    return res.status(503).json({ ok: false, error: 'WhatsApp client no está listo aún — escanea el QR' })
  }

  try {
    // Normalizar número: quitar todo excepto dígitos, luego añadir @c.us
    const chatId = phone.replace(/\D/g, '') + '@c.us'
    await client.sendMessage(chatId, message)
    console.log(`✉️   Mensaje enviado a ${chatId}`)
    res.json({ ok: true, to: chatId })
  } catch (err) {
    console.error('Error enviando mensaje WhatsApp:', err.message)
    res.status(500).json({ ok: false, error: err.message })
  }
})

// ── Arranque ───────────────────────────────────────────────────────────────────

const PORT = process.env.PORT || 3001
app.listen(PORT, () => {
  console.log(`🚀  WhatsApp bot HTTP server corriendo en puerto ${PORT}`)
})
