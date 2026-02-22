# SecurePay Frontend - Enhanced UI

Modern, user-friendly frontend for the biometric payment verification system with support for both BANK and SOLANA payment rails.

## Features

- **Modern Dark Theme** - Beautiful gradient UI with smooth animations
- **Dual Payment Rails** - Support for both traditional banking (Fiserv) and blockchain (Solana)
- **Real-time Liveness Detection** - 3-second video capture with webcam
- **Multi-stage Verification Pipeline**:
  - Deepfake detection
  - Liveness checking
  - Quality assessment
  - Presage behavioral analysis
  - Gemini AI pattern recognition
- **Blockchain Receipts** - Immutable verification records on Solana
- **Voice Authentication** - Audio confirmation playback
- **Comprehensive Audit Log** - View all challenges and verification results
- **Responsive Design** - Works on desktop and mobile devices

## Tech Stack

- **React 18** - Modern React with hooks
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **React Router** - Client-side routing
- **CSS3** - Custom animations and modern styling

## Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:3000`

3. **Build for production**:
   ```bash
   npm run build
   ```

4. **Preview production build**:
   ```bash
   npm run preview
   ```

## Configuration

The frontend expects the backend API to be running at `http://localhost:8000`. You can modify this in `src/api.ts` if needed.

## Project Structure

```
frontend-enhanced/
├── src/
│   ├── components/         # Reusable UI components
│   │   ├── AudioPlayer.tsx # Voice audio playback
│   │   ├── ChallengeModal.tsx # Liveness verification modal
│   │   └── ScoreCard.tsx   # Verification score display
│   ├── pages/              # Main application pages
│   │   ├── Home.tsx        # Payment initiation form
│   │   ├── Result.tsx      # Payment result display
│   │   └── Audit.tsx       # Challenge audit log
│   ├── api.ts              # API client functions
│   ├── App.tsx             # Main app component with routing
│   ├── main.tsx            # Application entry point
│   └── styles.css          # Global styles
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Usage

### Initiating a Payment

1. Navigate to the home page
2. Enter user ID (default: "demo_user")
3. Select payment rail (BANK or SOLANA)
4. Enter amount
5. Provide recipient details:
   - **BANK**: Recipient ID
   - **SOLANA**: Wallet address
6. Add optional payment note
7. Click "Initiate Payment"

### Liveness Challenge

If verification is required:
1. A modal will appear with instructions
2. Allow camera access when prompted
3. Position your face in the frame
4. Wait for 3-second countdown
5. Follow the on-screen prompt
6. Recording happens automatically
7. Wait for multi-stage verification pipeline

### Viewing Results

The result page displays:
- **Decision Badge** - APPROVED, REJECTED, or RETRY
- **Payment Details** - ID, status, rail
- **Blockchain Transactions** - For Solana payments
- **Verification Scores** - Detailed metrics with grades
- **Analysis Reasons** - Explanation of decision
- **Voice Confirmation** - Audio playback
- **Retry Option** - If decision is RETRY (one attempt allowed)

### Audit Log

View all verification challenges:
- Click on any row to see detailed information
- View scores, reasons, and blockchain transactions
- Filter and search capabilities

## API Endpoints Used

- `POST /payments/initiate` - Start payment process
- `POST /liveness/upload` - Upload verification video
- `GET /audit/challenges` - List all challenges
- `GET /audit/challenges/{id}` - Get challenge details

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Note**: Webcam access required for liveness verification.

## Security Features

- Device fingerprinting for fraud detection
- Multi-layer AI verification pipeline
- Blockchain-based audit trail
- Real-time deepfake detection
- Behavioral pattern analysis

## Development

The frontend uses React with TypeScript for type safety. All components are functional components using React hooks.

### Key Components

- **Home** - Main payment form with rail selection
- **ChallengeModal** - Handles webcam recording and upload
- **Result** - Displays verification results with scores
- **Audit** - Lists and displays challenge details
- **AudioPlayer** - Custom audio player with controls
- **ScoreCard** - Visual score display with grades

### State Management

Local state management using React hooks (`useState`, `useEffect`, `useRef`). Navigation state passed via React Router's `location.state`.

## License

Proprietary - Hackathon MVP
