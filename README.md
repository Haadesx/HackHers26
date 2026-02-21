# Payment Liveness Frontend

React + TypeScript + Vite frontend for the hackathon MVP supporting BANK and SOLANA payment rails with liveness verification.

## Setup

Install dependencies:

```bash
npm install
```

## Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Build

Build for production:

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

## Features

### Home Page
- Payment form with rail selector (BANK/SOLANA)
- Conditional fields based on rail selection
- Device ID tracking in localStorage
- Automatic challenge modal on CHALLENGE_REQUIRED response

### Challenge Modal
- 3-second webcam video recording
- Real-time progress tracking
- Multi-stage upload progress display:
  - Uploading
  - Deepfake/Liveness analysis
  - Presage Sensing
  - Gemini Pattern Check
  - Executing (Bank/Solana)

### Result Page
- Payment status and details
- Verification scores display
- Decision badge (APPROVED/RETRY/DENIED)
- Solana transaction links
- Audio playback with autoplay fallback
- Retry functionality (one attempt)

### Audit Page
- Table view of all challenges
- Click to view detailed challenge information
- Modal with full verification scores

## API Configuration

Backend API is configured to run at `http://localhost:8000`

Update `src/api.ts` to change the API base URL.

## Browser Requirements

- Modern browser with MediaRecorder API support
- Camera access for liveness challenges
- Audio playback capability
