import { NextRequest, NextResponse } from 'next/server'
import { writeFile, mkdir, readdir, unlink } from 'fs/promises'
import { join } from 'path'
import { existsSync } from 'fs'

const DIR = join(process.cwd(), 'public', 'uploads', 'avatars')

async function clearAvatar() {
  if (!existsSync(DIR)) return
  const files = await readdir(DIR)
  await Promise.all(
    files.filter(f => f.startsWith('avatar.')).map(f => unlink(join(DIR, f)))
  )
}

export async function POST(req: NextRequest) {
  try {
    const file = (await req.formData()).get('avatar') as File | null
    if (!file) return NextResponse.json({ error: 'No file' }, { status: 400 })

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type))
      return NextResponse.json({ error: 'Tipo no válido' }, { status: 400 })
    if (file.size > 2 * 1024 * 1024)
      return NextResponse.json({ error: 'Máx 2MB' }, { status: 400 })

    await clearAvatar()
    if (!existsSync(DIR)) await mkdir(DIR, { recursive: true })

    const ext = { 'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp' }[file.type]!
    const filename = `avatar.${ext}`
    await writeFile(join(DIR, filename), Buffer.from(await file.arrayBuffer()))

    return NextResponse.json({ avatarUrl: `/uploads/avatars/${filename}?t=${Date.now()}` })
  } catch {
    return NextResponse.json({ error: 'Error interno' }, { status: 500 })
  }
}

export async function DELETE() {
  try {
    await clearAvatar()
    return NextResponse.json({ ok: true })
  } catch {
    return NextResponse.json({ error: 'Error interno' }, { status: 500 })
  }
}
