async function test() {
  for (let i = 0; i < 10; i++) {
    try {
      const start = Date.now();
      const res = await fetch('http://api:8000/');
      console.log(`[${i}] Status: ${res.status} (${Date.now() - start}ms)`);
    } catch (e) {
      console.error(`[${i}] Failed:`, e.message);
    }
  }
}
test();
