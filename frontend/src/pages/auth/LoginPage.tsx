import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, Cpu, Zap, Activity } from 'lucide-react';
import { useAppDispatch } from '@/store';
import { setCredentials } from '@/store/authSlice';
import { authService } from '@/services/authService';
import { ROLE_DASHBOARD_ROUTES } from '@/constants';
import { mechanicService } from '@/services/ticketService';

const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [error, setError] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (values: LoginForm) => {
    setError('');
    try {
      const { tokens, user } = await authService.login(values);
      dispatch(setCredentials({
        user,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
      }));
      if (user.role === 'mechanic') {
        try {
          await mechanicService.updateStatus(user.user_id, 'available');
        } catch (e) {
          console.error('Failed to set mechanic status to available', e);
        }
      }
      
      navigate(ROLE_DASHBOARD_ROUTES[user.role], { replace: true });
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setError('Invalid email or password. Please try again.');
      } else if (err?.code === 'ERR_NETWORK' || !err?.response) {
        setError('Cannot reach the server. Please ensure the backend is running.');
      } else {
        setError(err?.response?.data?.detail || 'Something went wrong. Please try again.');
      }
    }
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left panel — branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 relative overflow-hidden">
        {/* Grid background */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `
              linear-gradient(hsl(199 89% 48% / 0.3) 1px, transparent 1px),
              linear-gradient(90deg, hsl(199 89% 48% / 0.3) 1px, transparent 1px)
            `,
            backgroundSize: '40px 40px',
          }}
        />
        {/* Glow orbs */}
        <div className="absolute top-1/4 left-1/4 w-64 h-64 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute bottom-1/3 right-1/4 w-48 h-48 rounded-full bg-purple-500/10 blur-3xl" />

        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="relative flex items-center gap-3"
        >
          <div className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/30 flex items-center justify-center">
            <Cpu className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">EdgeTwin AI</h1>
            <p className="text-xs text-muted-foreground">Predictive Maintenance Platform</p>
          </div>
        </motion.div>

        {/* Hero text */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="relative"
        >
          <h2 className="text-4xl font-bold leading-tight mb-4">
            Industry 4.0<br />
            <span className="gradient-text">Predictive Intelligence</span>
          </h2>
          <p className="text-muted-foreground text-lg leading-relaxed">
            AI-powered machine health monitoring, real-time digital twins,
            and intelligent maintenance workflow orchestration.
          </p>

          {/* Feature pills */}
          <div className="flex flex-wrap gap-3 mt-8">
            {[
              { icon: Activity, label: 'Real-time Monitoring' },
              { icon: Zap, label: 'ML Predictions' },
              { icon: Cpu, label: 'Digital Twin' },
            ].map(({ icon: Icon, label }) => (
              <div
                key={label}
                className="flex items-center gap-2 px-4 py-2 rounded-full glass text-sm text-muted-foreground"
              >
                <Icon className="w-3.5 h-3.5 text-primary" />
                {label}
              </div>
            ))}
          </div>
        </motion.div>

        {/* Stats */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="relative grid grid-cols-3 gap-4"
        >
          {[
            { value: '99.7%', label: 'Uptime SLA' },
            { value: '<2ms', label: 'Inference Latency' },
            { value: '6 Roles', label: 'RBAC Levels' },
          ].map(({ value, label }) => (
            <div key={label} className="glass-card rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-primary">{value}</p>
              <p className="text-xs text-muted-foreground mt-1">{label}</p>
            </div>
          ))}
        </motion.div>
      </div>

      {/* Right panel — login form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-10">
            <div className="w-9 h-9 rounded-xl bg-primary/20 border border-primary/30 flex items-center justify-center">
              <Cpu className="w-4 h-4 text-primary" />
            </div>
            <h1 className="text-lg font-bold">EdgeTwin AI</h1>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-foreground">Welcome back</h2>
            <p className="text-muted-foreground mt-1">Sign in to your dashboard</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
            {/* Email */}
            <div className="space-y-1.5">
              <label htmlFor="email" className="text-sm font-medium text-foreground">
                Email address
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@factory.com"
                className="w-full h-11 px-4 rounded-lg bg-secondary border border-border text-sm
                           placeholder:text-muted-foreground focus:outline-none focus:ring-2
                           focus:ring-primary/50 focus:border-primary transition-colors"
                {...register('email')}
              />
              {errors.email && (
                <p className="text-xs text-destructive">{errors.email.message}</p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label htmlFor="password" className="text-sm font-medium text-foreground">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                className="w-full h-11 px-4 rounded-lg bg-secondary border border-border text-sm
                           placeholder:text-muted-foreground focus:outline-none focus:ring-2
                           focus:ring-primary/50 focus:border-primary transition-colors"
                {...register('password')}
              />
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>

            {/* Error */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-lg bg-destructive/10 border border-destructive/30 px-4 py-3"
              >
                <p className="text-sm text-destructive">{error}</p>
              </motion.div>
            )}

            {/* Submit */}
            <button
              id="login-submit-btn"
              type="submit"
              disabled={isSubmitting}
              className="w-full h-11 rounded-lg bg-primary text-primary-foreground font-semibold
                         text-sm transition-all duration-200 hover:brightness-110 active:scale-[0.98]
                         disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Signing in…
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          <p className="text-center text-xs text-muted-foreground mt-8">
            Access is managed by your system administrator.
          </p>
        </motion.div>
      </div>
    </div>
  );
}
