const yearTrendsCharts = document.getElementById("year-trends-charts");
const trendCategory = document.getElementById("trend-category");
const toast = document.getElementById("toast");
const trendChartInstances = [];

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.className = "toast show" + (isError ? " error" : "");
  setTimeout(() => toast.classList.remove("show"), 3000);
}

function formatMoney(amount) {
  return new Intl.NumberFormat("en-LK", {
    style: "currency",
    currency: "LKR",
  }).format(amount);
}

async function fetchJSON(url) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

function destroyTrendCharts() {
  trendChartInstances.forEach((chart) => chart.destroy());
  trendChartInstances.length = 0;
}

function chartLabel(category) {
  return category ? `Expenses — ${category} (LKR)` : "Expenses (LKR)";
}

function renderYearTrendCharts(data) {
  destroyTrendCharts();
  const category = data.category || "";

  if (!data.years || !data.years.length) {
    yearTrendsCharts.innerHTML = category
      ? `<p class="empty-state">No expenses found in category "${category}".</p>`
      : '<p class="empty-state">No expense data yet. Add expenses on the Dashboard to see yearly trends.</p>';
    return;
  }

  yearTrendsCharts.innerHTML = data.years
    .map((year) => {
      const trend = data.trends[String(year)];
      return `
        <div class="trend-chart-card">
          <div class="trend-chart-header">
            <h3>${year}${category ? ` · ${category}` : ""}</h3>
            <span class="trend-year-total">Year total: ${formatMoney(trend.year_total)}</span>
          </div>
          <div class="trend-chart-wrap">
            <canvas id="trend-chart-${year}" aria-label="Monthly expense trend for ${year}"></canvas>
          </div>
        </div>
      `;
    })
    .join("");

  data.years.forEach((year) => {
    const trend = data.trends[String(year)];
    const canvas = document.getElementById(`trend-chart-${year}`);
    const chart = new Chart(canvas, {
      type: "line",
      data: {
        labels: trend.labels,
        datasets: [
          {
            label: chartLabel(category),
            data: trend.totals,
            borderColor: "#43a047",
            backgroundColor: "rgba(67, 160, 71, 0.15)",
            borderWidth: 2,
            fill: true,
            tension: 0.3,
            pointBackgroundColor: "#2e7d32",
            pointRadius: 4,
            pointHoverRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => formatMoney(ctx.parsed.y),
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (value) =>
                new Intl.NumberFormat("en-LK", {
                  notation: "compact",
                  compactDisplay: "short",
                }).format(value),
            },
            grid: { color: "rgba(184, 223, 196, 0.5)" },
          },
          x: {
            grid: { display: false },
          },
        },
      },
    });
    trendChartInstances.push(chart);
  });
}

async function loadTrends() {
  const category = trendCategory.value;
  let url = "/api/trends";
  if (category) url += `?category=${encodeURIComponent(category)}`;
  const data = await fetchJSON(url);
  renderYearTrendCharts(data);
}

trendCategory.addEventListener("change", () => {
  loadTrends().catch((err) => showToast(err.message, true));
});

loadTrends().catch((err) => showToast(err.message, true));
