import { useEffect, useRef, useState } from 'react';
import { uploadVideo, UploadVideoResponse } from '../api';

interface ChallengeModalProps {
  challengeId: string;
  prompt: string;
  expiresAt: string;
  onComplete: (result: UploadVideoResponse) => void;
  onClose: () => void;
}

type ProgressStage =
  | 'recording'
  | 'uploading'
  | 'deepfake_liveness'
  | 'presage'
  | 'gemini'
  | 'executing';

export function ChallengeModal({
  challengeId,
  prompt,
  expiresAt,
  onComplete,
  onClose,
}: ChallengeModalProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const [countdown, setCountdown] = useState<number>(0);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingProgress, setRecordingProgress] = useState(0);
  const [progressStage, setProgressStage] = useState<ProgressStage>('recording');
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const expires = new Date(expiresAt).getTime();
    const updateCountdown = () => {
      const now = Date.now();
      const remaining = Math.max(0, Math.floor((expires - now) / 1000));
      setCountdown(remaining);
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [expiresAt]);

  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, []);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: false,
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      setError('Failed to access camera');
      console.error('Camera error:', err);
    }
  };

  const stopCamera = () => {
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
    }
  };

  const startRecording = async () => {
    if (!videoRef.current?.srcObject) {
      setError('Camera not ready');
      return;
    }

    try {
      const stream = videoRef.current.srcObject as MediaStream;
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'video/webm',
      });

      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const videoBlob = new Blob(chunksRef.current, { type: 'video/webm' });
        await handleUpload(videoBlob);
      };

      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
      setRecordingProgress(0);

      const duration = 3000;
      const interval = 50;
      let elapsed = 0;

      const progressInterval = setInterval(() => {
        elapsed += interval;
        setRecordingProgress((elapsed / duration) * 100);

        if (elapsed >= duration) {
          clearInterval(progressInterval);
          mediaRecorder.stop();
          setIsRecording(false);
        }
      }, interval);
    } catch (err) {
      setError('Failed to start recording');
      console.error('Recording error:', err);
    }
  };

  const handleUpload = async (videoBlob: Blob) => {
    try {
      setProgressStage('uploading');
      await new Promise(resolve => setTimeout(resolve, 500));

      setProgressStage('deepfake_liveness');
      await new Promise(resolve => setTimeout(resolve, 500));

      setProgressStage('presage');
      await new Promise(resolve => setTimeout(resolve, 500));

      setProgressStage('gemini');
      await new Promise(resolve => setTimeout(resolve, 500));

      setProgressStage('executing');

      const result = await uploadVideo(challengeId, videoBlob);
      stopCamera();
      onComplete(result);
    } catch (err) {
      setError('Upload failed');
      console.error('Upload error:', err);
    }
  };

  const getProgressLabel = () => {
    switch (progressStage) {
      case 'recording':
        return isRecording ? 'Recording...' : 'Ready to record';
      case 'uploading':
        return 'Uploading';
      case 'deepfake_liveness':
        return 'Deepfake/Liveness';
      case 'presage':
        return 'Presage Sensing';
      case 'gemini':
        return 'Gemini Pattern Check';
      case 'executing':
        return 'Executing (Bank/Solana)';
    }
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-content">
        <button className="modal-close" onClick={onClose}>×</button>

        <h2>Liveness Challenge</h2>

        <div className="challenge-info">
          <p className="challenge-prompt">{prompt}</p>
          <p className="challenge-countdown">
            Time remaining: {Math.floor(countdown / 60)}:{(countdown % 60).toString().padStart(2, '0')}
          </p>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="video-container">
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            className="camera-preview"
          />
        </div>

        {isRecording && (
          <div className="recording-progress">
            <div className="progress-bar" style={{ width: `${recordingProgress}%` }} />
          </div>
        )}

        <div className="progress-label">{getProgressLabel()}</div>

        {!isRecording && progressStage === 'recording' && (
          <button onClick={startRecording} className="record-button">
            Start Recording
          </button>
        )}
      </div>
    </div>
  );
}
