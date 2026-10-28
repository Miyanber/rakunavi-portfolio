const ctx = document.getElementById('cpuChart').getContext('2d');

const cpuChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            { label: 'CPU (%)', data: [] },
            { label: 'Memory (%)', data: [] },
            { label: 'Swap (%)', data: [] }
        ]
    },
    options: {
        scales: {
            y: { beginAtZero: true, max: 100 }
        }
    }
});

async function updateStats() {
    const res = await fetch("/system_stats/");
    const json = await res.json();

    const timeLabel = new Date().toLocaleTimeString();
    cpuChart.data.labels.push(timeLabel);

    // ---- グラフ更新 ----
    cpuChart.data.datasets[0].data.push(json.cpu);
    cpuChart.data.datasets[1].data.push(json.memory);
    cpuChart.data.datasets[2].data.push(json.swap);

    // データ数を制限
    if (cpuChart.data.labels.length > 20) {
        cpuChart.data.labels.shift();
        cpuChart.data.datasets.forEach(ds => ds.data.shift());
    }

    cpuChart.update();

    // ---- 文字表示更新 ----
    document.getElementById("cpuValue").textContent = json.cpu.toFixed(1);
    document.getElementById("memoryValue").textContent = json.memory.toFixed(1);
    document.getElementById("swapValue").textContent = json.swap.toFixed(1);
}

// 2秒ごとに更新
setInterval(updateStats, 2000);
