const dashboardCategory = document.getElementById("dashboard-category");
const dashboardYear = document.getElementById("dashboard-year");
const dashboardMonth = document.getElementById("dashboard-month");
const dashboardTotal = document.getElementById("dashboard-total");
const dashboardCount = document.getElementById("dashboard-count");
const dashboardChart = document.getElementById("dashboard-chart");
const toast = document.getElementById("toast");

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
  const res = await fetch(url);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function loadDashboard() {
  const params = new URLSearchParams({
    year: dashboardYear.value,
  });

  if (dashboardMonth.value) params.set("month", dashboardMonth.value);
  if (dashboardCategory.value) params.set("category", dashboardCategory.value);

  const data = await fetchJSON(`/api/dashboard?${params.toString()}`);
  dashboardTotal.textContent = formatMoney(data.total);
  dashboardCount.textContent = data.count;
  renderDashboardChart(data.chart);
}

function renderDashboardChart(points) {
  const hasSpend = points.some((point) => point.total > 0);
  if (!points.length || !hasSpend) {
    dashboardChart.innerHTML = '<p class="empty-state">No expenses for these filters</p>';
    return;
  }

  const max = Math.max(...points.map((point) => point.total));
  const width = 900;
  const height = 320;
  const padding = { top: 28, right: 32, bottom: 48, left: 72 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const divisor = Math.max(points.length - 1, 1);
  const coordinates = points.map((point, index) => {
    const x = padding.left + (index / divisor) * plotWidth;
    const y = padding.top + plotHeight - (point.total / max) * plotHeight;
    return { ...point, x, y };
  });
  const linePath = coordinates
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
    .join(" ");
  const areaPath = `${linePath} L ${coordinates[coordinates.length - 1].x} ${padding.top + plotHeight} L ${coordinates[0].x} ${padding.top + plotHeight} Z`;
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
    const value = max * ratio;
    const y = padding.top + plotHeight - ratio * plotHeight;
    return { value, y };
  });

  dashboardChart.innerHTML = `
    <svg class="dashboard-line-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Expense trend line chart">
      <g class="chart-grid">
        ${yTicks
          .map(
            (tick) => `
          <line x1="${padding.left}" y1="${tick.y}" x2="${width - padding.right}" y2="${tick.y}"></line>
          <text x="${padding.left - 12}" y="${tick.y + 4}" text-anchor="end">${formatCompactMoney(tick.value)}</text>
        `
          )
          .join("")}
      </g>
      <path class="chart-area" d="${areaPath}"></path>
      <path class="chart-line" d="${linePath}"></path>
      <g class="chart-points">
        ${coordinates
          .map(
            (point) => `
          <g>
            <circle cx="${point.x}" cy="${point.y}" r="5"></circle>
            <title>${escapeHtml(point.label)}: ${formatMoney(point.total)}</title>
          </g>
        `
          )
          .join("")}
      </g>
      <g class="chart-labels">
        ${coordinates
          .map(
            (point) => `
          <text x="${point.x}" y="${height - 16}" text-anchor="middle">${escapeHtml(point.label)}</text>
        `
          )
          .join("")}
      </g>
    </svg>
  `;
}

function formatCompactMoney(amount) {
  if (amount >= 1000000) return `Rs. ${(amount / 1000000).toFixed(1)}M`;
  if (amount >= 1000) return `Rs. ${(amount / 1000).toFixed(1)}K`;
  return `Rs. ${Math.round(amount)}`;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

[dashboardCategory, dashboardYear, dashboardMonth].forEach((control) => {
  control.addEventListener("change", () => {
    loadDashboard().catch((err) => showToast(err.message, true));
  });
});

loadDashboard().catch((err) => showToast(err.message, true));
