import { ToastItem, useToastStore } from '../lib/toastStore';
import './Toast.css';

interface ToastProps {
  toast: ToastItem;
}

export function Toast({ toast }: ToastProps) {
  const removeToast = useToastStore((s) => s.removeToast);

  return (
    <div 
      className={`toast toast--${toast.type}`}
      onClick={() => removeToast(toast.id)}
    >
      <div className="toast__content">
        <span className="toast__message">{toast.message}</span>
      </div>
    </div>
  );
}
