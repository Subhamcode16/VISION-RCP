import { useToastStore } from '../lib/toastStore';
import { Toast } from './Toast';

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);

  return (
    <div className="toaster">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} />
      ))}
    </div>
  );
}
