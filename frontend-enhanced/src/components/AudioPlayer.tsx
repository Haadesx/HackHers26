import { useState, useRef, useEffect } from 'react'
import { VoiceAudio } from '../api'

interface Props {
  voiceAudio: VoiceAudio
}

export default function AudioPlayer({ voiceAudio }: Props) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [audioUrl, setAudioUrl] = useState('')
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    if (voiceAudio.type === 'url') {
      setAudioUrl(voiceAudio.data)
    } else if (voiceAudio.type === 'base64') {
      const byteCharacters = atob(voiceAudio.data)
      const byteNumbers = new Array(byteCharacters.length)
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i)
      }
      const byteArray = new Uint8Array(byteNumbers)
      const blob = new Blob([byteArray], { type: 'audio/mpeg' })
      const url = URL.createObjectURL(blob)
      setAudioUrl(url)

      return () => URL.revokeObjectURL(url)
    }
  }, [voiceAudio])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleLoadedMetadata = () => {
      setDuration(audio.duration)
    }

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime)
    }

    const handleEnded = () => {
      setIsPlaying(false)
      setCurrentTime(0)
    }

    audio.addEventListener('loadedmetadata', handleLoadedMetadata)
    audio.addEventListener('timeupdate', handleTimeUpdate)
    audio.addEventListener('ended', handleEnded)

    // Try autoplay
    const attemptAutoplay = async () => {
      try {
        await audio.play()
        setIsPlaying(true)
      } catch {
        // Autoplay blocked, user interaction required
      }
    }
    attemptAutoplay()

    return () => {
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata)
      audio.removeEventListener('timeupdate', handleTimeUpdate)
      audio.removeEventListener('ended', handleEnded)
    }
  }, [audioUrl])

  const togglePlay = async () => {
    const audio = audioRef.current
    if (!audio) return

    if (isPlaying) {
      audio.pause()
      setIsPlaying(false)
    } else {
      try {
        await audio.play()
        setIsPlaying(true)
      } catch (err) {
        console.error('Failed to play audio:', err)
      }
    }
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current
    if (!audio) return

    const time = parseFloat(e.target.value)
    audio.currentTime = time
    setCurrentTime(time)
  }

  const formatTime = (time: number) => {
    if (!isFinite(time)) return '0:00'
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  return (
    <div className="audio-player">
      <audio ref={audioRef} src={audioUrl} />

      <div className="audio-controls">
        <button
          className="audio-play-btn"
          onClick={togglePlay}
          aria-label={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? '⏸️' : '▶️'}
        </button>

        <div className="audio-timeline">
          <span className="audio-time">{formatTime(currentTime)}</span>

          <input
            type="range"
            className="audio-slider"
            min="0"
            max={duration || 0}
            value={currentTime}
            onChange={handleSeek}
            step="0.1"
          />

          <span className="audio-time">{formatTime(duration)}</span>
        </div>

        <div className="audio-visualizer">
          {isPlaying ? (
            <>
              <span className="visualizer-bar"></span>
              <span className="visualizer-bar"></span>
              <span className="visualizer-bar"></span>
              <span className="visualizer-bar"></span>
            </>
          ) : (
            <span className="audio-status">🔊</span>
          )}
        </div>
      </div>
    </div>
  )
}
