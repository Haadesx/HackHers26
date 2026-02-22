const API_BASE = 'http://localhost:8000'

export interface InitiatePaymentRequest {
  user_id: string
  rail: 'BANK' | 'SOLANA'
  amount: number
  recipient_id?: string
  recipient_address?: string | null
  note: string
  device_id: string
  user_agent: string
  ip?: string | null
}

export interface ApprovedResponse {
  status: 'APPROVED'
  payment_id: string
  payment_status: string
  rail: 'BANK' | 'SOLANA'
  solana_tx?: string
  voice_audio?: VoiceAudio
}

export interface ChallengeRequiredResponse {
  status: 'CHALLENGE_REQUIRED'
  challenge_id: string
  prompt: string
  security_message?: string
  expires_at: string
  payment_id: string
  payment_status: string
  rail: 'BANK' | 'SOLANA'
  solana_tx?: string
}

export type InitiatePaymentResponse = ApprovedResponse | ChallengeRequiredResponse

export interface VerificationResponse {
  status: 'VERIFIED'
  decision: 'APPROVED' | 'REJECTED' | 'RETRY'
  scores: {
    deepfake_mean: number
    deepfake_var: number
    liveness: number
    quality: number
    presage: number
  }
  reasons: string[]
  challenge_id?: string
  payment_id: string
  payment_status: string
  rail: 'BANK' | 'SOLANA'
  solana_tx?: string
  verification_receipt_tx?: string
}

export interface Challenge {
  id: string
  user_id: string
  created_at: string
  prompt: string
  decision?: string
  payment_id?: string
  rail?: string
}

export interface ChallengeDetail extends Challenge {
  scores?: {
    deepfake_mean: number
    deepfake_var: number
    liveness: number
    quality: number
    presage: number
  }
  reasons?: string[]
  payment_status?: string
  solana_tx?: string
  verification_receipt_tx?: string
}

export async function initiatePayment(data: InitiatePaymentRequest): Promise<InitiatePaymentResponse> {
  const response = await fetch(`${API_BASE}/payments/initiate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to initiate payment' }))
    throw new Error(error.detail || 'Failed to initiate payment')
  }

  return response.json()
}

export async function uploadLivenessVideo(
  challengeId: string,
  videoBlob: Blob
): Promise<VerificationResponse> {
  const formData = new FormData()
  formData.append('video', videoBlob, 'liveness.webm')

  const response = await fetch(`${API_BASE}/liveness/upload?challenge_id=${challengeId}`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to upload video' }))
    throw new Error(error.detail || 'Failed to upload video')
  }

  return response.json()
}

export async function getChallenges(): Promise<Challenge[]> {
  const response = await fetch(`${API_BASE}/audit/challenges`)

  if (!response.ok) {
    throw new Error('Failed to fetch challenges')
  }

  const data = await response.json()
  // Backend wraps in { challenges: [...] } with challenge_id/transfer_id keys
  const raw = data.challenges || data
  return (Array.isArray(raw) ? raw : []).map((c: any) => ({
    id: c.challenge_id || c.id,
    user_id: c.user_id,
    created_at: c.created_at,
    prompt: c.prompt,
    decision: c.decision,
    payment_id: c.transfer_id || c.payment_id,
    rail: c.rail,
  }))
}

export async function getChallengeDetail(id: string): Promise<ChallengeDetail> {
  const response = await fetch(`${API_BASE}/audit/challenges/${id}`)

  if (!response.ok) {
    throw new Error('Failed to fetch challenge detail')
  }

  const c = await response.json()
  // Map backend field names to frontend interface
  return {
    id: c.challenge_id || c.id,
    user_id: c.user_id,
    created_at: c.created_at,
    prompt: c.prompt,
    decision: c.decision,
    payment_id: c.transfer_id || c.payment_id,
    rail: c.rail,
    scores: c.scores,
    reasons: c.reasons,
    payment_status: c.payment_status,
    solana_tx: c.solana_tx,
    verification_receipt_tx: c.verification_receipt_tx,
  }
}

export function getDeviceId(): string {
  let deviceId = localStorage.getItem('device_id')
  if (!deviceId) {
    deviceId = `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    localStorage.setItem('device_id', deviceId)
  }
  return deviceId
}
