import { useParams, useNavigate } from 'react-router-dom';
import App from '../App';

export default function GamePage() {
  const { id } = useParams();
  // id from route: if "new" or undefined → ConnectOverlay
  // if a real session ID → App hydrates from backend
  const campaignId = (!id || id === 'new') ? null : id;

  return <App campaignId={campaignId} />;
}
