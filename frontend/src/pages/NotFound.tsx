import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '@/hooks/useAuth';

export default function NotFound() {
  const navigate = useNavigate();
  const { dashboardRoute, isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <p className="text-8xl font-bold gradient-text mb-4">404</p>
        <h1 className="text-2xl font-bold text-foreground mb-2">Page not found</h1>
        <p className="text-muted-foreground mb-8">
          The page you are looking for does not exist.
        </p>
        <button
          onClick={() => navigate(isAuthenticated ? dashboardRoute : '/login')}
          className="px-6 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium text-sm
                     hover:brightness-110 transition-all"
        >
          {isAuthenticated ? 'Go to Dashboard' : 'Back to Login'}
        </button>
      </motion.div>
    </div>
  );
}
