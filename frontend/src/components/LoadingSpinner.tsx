import './LoadingSpinner.css';

interface Props {
  message?: string;
}

export default function LoadingSpinner({ message }: Props) {
  return (
    <div className="spinner-container">
      <div className="spinner-ring"></div>
      {message && <p className="spinner-message">{message}</p>}
    </div>
  );
}
