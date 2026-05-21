/**
 * Exports — Export format selector, download page, and platform prompt package generator.
 * @module pages/Exports
 */
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { StageInterlude, Whisper } from '../components/tutorial'
import apiClient from '../lib/apiClient'
import { downloadBlob, formatFilename } from '../lib/exportUtils'

const FORMATS = [
  { id: 'md', label: 'Markdown', icon: '\u{1F4DD}', desc: 'Clean markdown document' },
  { id: 'txt', label: 'Plain Text', icon: '\u{1F4C4}', desc: 'Simple text format' },
  { id: 'pdf', label: 'PDF', icon: '\u{1F4D5}', desc: 'Professional PDF document' },
  { id: 'docx', label: 'Word', icon: '\u{1F4D8}', desc: 'Microsoft Word format' },
  { id: 'zip', label: 'ZIP Bundle', icon: '\u{1F4E6}', desc: 'All formats in one download' },
]

const PLATFORMS = [
  { id: 'cursor', label: 'Cursor', desc: 'VS Code AI composer instructions' },
  { id: 'bolt', label: 'Bolt.new', desc: 'Prompts for Bolt\'s interface' },
  { id: 'lovable', label: 'Lovable', desc: 'Prompts for Lovable\'s chat' },
  { id: 'replit', label: 'Replit', desc: 'Prompts for Replit Agent' },
  { id: 'claude-code', label: 'Claude Code', desc: 'CLI-formatted instructions' },
  { id: 'chatgpt', label: 'ChatGPT', desc: 'Prompts for GPT-4' },
  { id: 'generic', label: 'Generic', desc: 'Platform-agnostic prompts' },
]

export function Exports() {
  const { projectId } = useParams<{ projectId: string }>()
  const [selectedFormat, setSelectedFormat] = useState('md')
  const [downloading, setDownloading] = useState(false)

  // Prompt package state
  const [selectedPlatform, setSelectedPlatform] = useState('cursor')
  const [generatingPackage, setGeneratingPackage] = useState(false)
  const [packageError, setPackageError] = useState<string | null>(null)

  const handleExport = async () => {
    if (!projectId) return
    setDownloading(true)
    try {
      const response = await apiClient.get(`/projects/${projectId}/export`, {
        params: { format: selectedFormat },
        responseType: 'blob',
      })
      const filename = formatFilename('design-kit', selectedFormat)
      downloadBlob(response.data, filename)
    } catch (err) {
      console.error('Export failed:', err)
    } finally {
      setDownloading(false)
    }
  }

  const handleSnapshot = async () => {
    if (!projectId) return
    try {
      await apiClient.post(`/library/${projectId}/snapshots`, {
        name: `Auto snapshot ${new Date().toLocaleString()}`,
        description: 'Saved from Export page',
      })
    } catch (err) {
      console.error('Snapshot failed:', err)
    }
  }

  const handlePromptPackage = async () => {
    if (!projectId) return
    setGeneratingPackage(true)
    setPackageError(null)
    try {
      const response = await apiClient.post(
        `/projects/${projectId}/export/prompt-package`,
        { platform: selectedPlatform },
        { responseType: 'blob', timeout: 120000 },
      )
      const filename = `prompt-package-${selectedPlatform}.zip`
      downloadBlob(response.data, filename)
    } catch (err: unknown) {
      console.error('Prompt package generation failed:', err)
      const axiosErr = err as { response?: { data?: Blob } }
      if (axiosErr.response?.data instanceof Blob) {
        try {
          const text = await axiosErr.response.data.text()
          const json = JSON.parse(text)
          setPackageError(json.detail || 'Generation failed. Please try again.')
        } catch {
          setPackageError('Generation failed. Please try again.')
        }
      } else {
        setPackageError('Generation failed. Please try again.')
      }
    } finally {
      setGeneratingPackage(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex">
      <StageInterlude
        phase="exports"
        message="Your design kit is ready. Choose a format and platform to export."
        stepIndex={4}
        totalSteps={5}
      />
      <Sidebar projectId={projectId} />
      <div className="ml-0 md:ml-[232px] pb-14 md:pb-0 flex-1 flex flex-col h-screen">
        <TopBar title="Export Design Kit" subtitle="Download your project artifacts">
          <Button variant="ghost" onClick={handleSnapshot}>Save Snapshot</Button>
        </TopBar>

        <div className="flex-1 p-4 md:p-6 overflow-y-auto pb-20 md:pb-6">
          {/* --- Design Kit Export --- */}
          <div className="max-w-3xl mx-auto mb-10">
            <h2 className="text-lg font-semibold text-white mb-1">Design Kit</h2>
            <p className="text-sm text-text-muted mb-5">Export your project design sheet in various formats.</p>

            <Whisper id="exports:formats" text="Pick a format to download your complete design kit">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 md:gap-4 mb-6">
              {FORMATS.map(fmt => (
                <button
                  key={fmt.id}
                  onClick={() => setSelectedFormat(fmt.id)}
                  className="text-left"
                >
                  <Card className={`transition-all cursor-pointer ${
                    selectedFormat === fmt.id ? 'border-accent shadow-[0_0_20px_rgba(0,229,255,0.1)]' : 'hover:border-white/15'
                  }`}>
                    <div className="text-2xl mb-2">{fmt.icon}</div>
                    <h3 className="text-sm font-semibold text-white">{fmt.label}</h3>
                    <p className="text-xs text-text-muted mt-1">{fmt.desc}</p>
                  </Card>
                </button>
              ))}
            </div>
            </Whisper>

            <div className="flex justify-center">
              <Button size="lg" onClick={handleExport} disabled={downloading}>
                {downloading ? 'Downloading...' : `Download ${FORMATS.find(f => f.id === selectedFormat)?.label || selectedFormat}`}
              </Button>
            </div>
          </div>

          {/* --- Divider --- */}
          <div className="max-w-3xl mx-auto border-t border-border mb-10" />

          {/* --- Prompt Package --- */}
          <div className="max-w-3xl mx-auto">
            <h2 className="text-lg font-semibold text-white mb-1">Prompt Package</h2>
            <p className="text-sm text-text-muted mb-5">
              Download a complete set of AI-ready prompts tailored to your project and chosen build platform.
              Includes step-by-step instructions.
            </p>

            <Card className="mb-6">
              <label htmlFor="platform-select" className="block text-xs font-medium text-text-muted mb-2">
                Target Platform
              </label>
              <select
                id="platform-select"
                value={selectedPlatform}
                onChange={(e) => setSelectedPlatform(e.target.value)}
                className="w-full bg-white/5 border border-border rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-accent transition-colors appearance-none cursor-pointer"
              >
                {PLATFORMS.map(p => (
                  <option key={p.id} value={p.id} className="bg-[#1a1a2e] text-white">
                    {p.label} — {p.desc}
                  </option>
                ))}
              </select>

              <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
                {PLATFORMS.map(p => (
                  <button
                    key={p.id}
                    onClick={() => setSelectedPlatform(p.id)}
                    className={`text-left rounded-lg border px-3 py-2 transition-all text-xs ${
                      selectedPlatform === p.id
                        ? 'border-accent bg-accent/10 text-accent'
                        : 'border-border bg-white/5 text-text-muted hover:border-white/20 hover:text-white'
                    }`}
                  >
                    <span className="font-medium">{p.label}</span>
                  </button>
                ))}
              </div>
            </Card>

            {packageError && (
              <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {packageError}
              </div>
            )}

            <div className="flex justify-center">
              <Button size="lg" onClick={handlePromptPackage} disabled={generatingPackage}>
                {generatingPackage ? 'Generating prompts...' : 'Generate & Download'}
              </Button>
            </div>

            {generatingPackage && (
              <p className="text-center text-xs text-text-muted mt-3">
                This may take 30-60 seconds while AI generates your custom prompts.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
