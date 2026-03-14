export async function fetchDefaults() {
    const res = await fetch('/api/defaults');
    if (!res.ok) throw new Error(`Failed to fetch defaults: ${res.status}`);
    return res.json();
}

export async function runSimulation(scenario) {
    const res = await fetch('/api/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scenario),
    });
    const data = await res.json();
    if (!res.ok && !data.errors) throw new Error(`Server error: ${res.status}`);
    return data;
}
