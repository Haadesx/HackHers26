import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Home } from './pages/Home';
import { Result } from './pages/Result';
import { Audit } from './pages/Audit';
import './styles.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/result" element={<Result />} />
        <Route path="/audit" element={<Audit />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
