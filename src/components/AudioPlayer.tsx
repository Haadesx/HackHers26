import { useEffect, useRef, useState } from 'react';
import { VoiceAudio } from '../api';

interface AudioPlayerProps {
  voiceAudio: VoiceAudio;
  autoplay?: boolean;
}

export function AudioPlayer({ voiceAudio, autoplay = true }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [audioUrl, setAudioUrl] = useState<string>('');
  const [canPlay, setCanPlay] = useState(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (voiceAudio.type === 'url') {
      setAudioUrl(voiceAudio.data);
    } else if (voiceAudio.type === 'base64') {
      try {
        const byteCharacters = atob(voiceAudio.data);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: 'audio/mpeg' });
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);

        return () => URL.revokeObjectURL(url);
      } catch (err) {
        setError('Failed to decode audio');
        console.error('Audio decode error:', err);
      }
    }
  }, [voiceAudio]);

  useEffect(() => {
    if (audioRef.current && audioUrl && canPlay && autoplay) {
      audioRef.current.play().catch((err) => {
        console.log('Autoplay prevented:', err);
      });
    }
  }, [audioUrl, canPlay, autoplay]);

  const handlePlay = () => {
    if (audioRef.current) {
      audioRef.current.play().catch((err) => {
        setError('Playback failed');
        console.error('Playback error:', err);
      });
    }
  };

  if (error) {
    return <div className="audio-error">{error}</div>;
  }

  if (!audioUrl) {
    return null;
  }

  return (
    <div className="audio-player">
      <audio
        ref={audioRef}
        src={audioUrl}
        onCanPlay={() => setCanPlay(true)}
        controls
      />
      <button onClick={handlePlay} className="play-button">
        Play Audio
      </button>
    </div>
  );
}
