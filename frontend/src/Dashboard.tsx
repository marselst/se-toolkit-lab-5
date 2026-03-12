import { useState, useEffect } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Bar, Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
)

// Types for API responses
interface ScoreBucket {
  bucket: string
  count: number
}

interface TimelineEntry {
  date: string
  submissions: number
}

interface PassRateEntry {
  task: string
  avg_score: number
  attempts: number
}

interface Lab {
  id: number
  title: string
}

interface ScoresData {
  labels: string[]
  datasets: {
    label: string
    data: number[]
    backgroundColor: string[]
  }[]
}

interface TimelineData {
  labels: string[]
  datasets: {
    label: string
    data: number[]
    borderColor: string
    backgroundColor: string
    tension: number
  }[]
}

const API_BASE = ''

function getApiKey(): string {
  return localStorage.getItem('api_key') ?? ''
}

async function fetchWithAuth(url: string): Promise<unknown> {
  const token = getApiKey()
  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return response.json()
}

export default function Dashboard() {
  const [labs, setLabs] = useState<Lab[]>([])
  const [selectedLab, setSelectedLab] = useState<string>('')
  const [scores, setScores] = useState<ScoreBucket[]>([])
  const [timeline, setTimeline] = useState<TimelineEntry[]>([])
  const [passRates, setPassRates] = useState<PassRateEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch labs on mount
  useEffect(() => {
    async function fetchLabs() {
      try {
        const data = await fetchWithAuth(`${API_BASE}/items/`)
        const items = data as Item[]
        const labItems = items.filter((item) => item.type === 'lab')
        setLabs(labItems.map((lab) => ({ id: lab.id, title: lab.title })))
        if (labItems.length > 0) {
          const labId = labIdFromTitle(labItems[0].title)
          setSelectedLab(labId)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch labs')
      }
    }
    fetchLabs()
  }, [])

  // Fetch analytics data when selectedLab changes
  useEffect(() => {
    if (!selectedLab) return

    async function fetchAnalytics() {
      setLoading(true)
      setError(null)
      try {
        const [scoresData, timelineData, passRatesData] = await Promise.all([
          fetchWithAuth(`${API_BASE}/analytics/scores?lab=${selectedLab}`),
          fetchWithAuth(`${API_BASE}/analytics/timeline?lab=${selectedLab}`),
          fetchWithAuth(`${API_BASE}/analytics/pass-rates?lab=${selectedLab}`),
        ])
        setScores(scoresData as ScoreBucket[])
        setTimeline(timelineData as TimelineEntry[])
        setPassRates(passRatesData as PassRateEntry[])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch analytics')
      } finally {
        setLoading(false)
      }
    }
    fetchAnalytics()
  }, [selectedLab])

  function handleLabChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setSelectedLab(e.target.value)
  }

  // Prepare chart data for scores
  const scoresChartData: ScoresData = {
    labels: scores.map((s) => s.bucket),
    datasets: [
      {
        label: 'Students',
        data: scores.map((s) => s.count),
        backgroundColor: [
          'rgba(255, 99, 132, 0.6)',
          'rgba(255, 159, 64, 0.6)',
          'rgba(75, 192, 192, 0.6)',
          'rgba(54, 162, 235, 0.6)',
        ],
      },
    ],
  }

  // Prepare chart data for timeline
  const timelineChartData: TimelineData = {
    labels: timeline.map((t) => t.date),
    datasets: [
      {
        label: 'Submissions',
        data: timeline.map((t) => t.submissions),
        borderColor: 'rgba(54, 162, 235, 1)',
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        tension: 0.3,
      },
    ],
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Analytics Dashboard</h1>
        <div className="lab-selector">
          <label htmlFor="lab-select">Select Lab: </label>
          <select
            id="lab-select"
            value={selectedLab}
            onChange={handleLabChange}
          >
            {labs.map((lab) => (
              <option key={lab.id} value={labIdFromTitle(lab.title)}>
                {lab.title}
              </option>
            ))}
          </select>
        </div>
      </header>

      {loading && <p className="loading">Loading analytics...</p>}
      {error && <p className="error">Error: {error}</p>}

      {!loading && !error && (
        <>
          <section className="chart-section">
            <h2>Score Distribution</h2>
            <Bar
              data={scoresChartData}
              options={{
                responsive: true,
                plugins: {
                  legend: { display: false },
                  title: {
                    display: true,
                    text: 'Students by Score Range',
                  },
                },
                scales: {
                  y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1 },
                  },
                },
              }}
            />
          </section>

          <section className="chart-section">
            <h2>Submissions Timeline</h2>
            <Line
              data={timelineChartData}
              options={{
                responsive: true,
                plugins: {
                  legend: { display: false },
                  title: {
                    display: true,
                    text: 'Submissions per Day',
                  },
                },
                scales: {
                  y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1 },
                  },
                },
              }}
            />
          </section>

          <section className="table-section">
            <h2>Pass Rates by Task</h2>
            <table>
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Avg Score</th>
                  <th>Attempts</th>
                </tr>
              </thead>
              <tbody>
                {passRates.map((entry) => (
                  <tr key={entry.task}>
                    <td>{entry.task}</td>
                    <td>{entry.avg_score}</td>
                    <td>{entry.attempts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  )
}

interface Item {
  id: number
  type: string
  title: string
  created_at: string
}

function labIdFromTitle(title: string): string {
  // Convert "Lab 04 — Testing" to "lab-04"
  const match = title.match(/Lab\s+(\d+)/i)
  if (match) {
    return `lab-${match[1].padStart(2, '0')}`
  }
  // Fallback: convert title to slug
  return title.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')
}
