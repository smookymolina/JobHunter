async function test() {
  try {
    console.log('Testing global fetch to http://api:8000/ ...');
    const res = await fetch('http://api:8000/');
    console.log('Status:', res.status);
    const data = await res.json();
    console.log('Data:', data);
  } catch (e) {
    console.error('Fetch failed:', e);
  }
}
test();
