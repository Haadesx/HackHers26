const API_BASE = 'http://localhost:8000';

export type Rail = 'BANK' | 'SOLANA';

export interface InitiatePaymentRequest {
  user_id: string;
  rail: Rail;
  amount: number;
  recipient_id?: string;
  recipient_address?: string;
  note: string;
  device_id: string;
  user_agent: string;
  ip?: string;
}

export interface VoiceAudio {
  type: 'url' | 'base64';
  data: string;
}

export interface ApprovedResponse {
  status: 'APPROVED';
  payment_id: string;
  payment_status: string;
  rail: Rail;
  solana_tx?: string;
  voice_audio?: VoiceAudio;
}

export interface ChallengeRequiredResponse {
  status: 'CHALLENGE_REQUIRED';
  challenge_id: string;
  prompt: string;
  expires_at: string;
  payment_id: string;
  payment_status: string;
  rail: Rail;
  solana_tx?: string;
}

export type InitiatePaymentResponse = ApprovedResponse | ChallengeRequiredResponse;

export interface VerificationScores {
  deepfake_mean: number;
  deepfake_var: number;
  liveness: number;
  quality: number;
  presage: number;
}

export interface UploadVideoResponse {
  status: 'VERIFIED';
  decision: string;
  scores: VerificationScores;
  reasons: string[];
  payment_id: string;
  payment_status: string;
  rail: Rail;
  solana_tx?: string;
  verification_receipt_tx?: string;
  voice_audio?: VoiceAudio;
}

export interface Challenge {
  id: string;
  user_id: string;
  prompt: string;
  created_at: string;
  decision?: string;
  scores?: VerificationScores;
}

export async function initiatePayment(data: InitiatePaymentRequest): Promise<InitiatePaymentResponse> {
  const response = await fetch(`${API_BASE}/payments/initiate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Payment initiation failed: ${response.statusText}`);
  }

  return response.json();
}

export async function uploadVideo(challengeId: string, videoBlob: Blob): Promise<UploadVideoResponse> {
  const formData = new FormData();
  formData.append('video', videoBlob, 'challenge.webm');

  const response = await fetch(`${API_BASE}/liveness/upload?challenge_id=${challengeId}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Video upload failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getChallenges(): Promise<Challenge[]> {
  const response = await fetch(`${API_BASE}/audit/challenges`);

  if (!response.ok) {
    throw new Error(`Failed to fetch challenges: ${response.statusText}`);
  }

  return response.json();
}

export async function getChallenge(id: string): Promise<Challenge> {
  const response = await fetch(`${API_BASE}/audit/challenges/${id}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch challenge: ${response.statusText}`);
  }

  return response.json();
}
