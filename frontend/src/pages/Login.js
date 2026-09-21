import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { seedAPI, getErrorMessage } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { TestTube, Eye, EyeOff, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await login(email, password);
      toast.success('Login successful!');
      navigate('/dashboard');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Invalid credentials'));
    } finally {
      setLoading(false);
    }
  };

  const handleSeedData = async () => {
    setSeeding(true);
    try {
      const response = await seedAPI.seed();
      toast.success('Demo data created! Use admin@lims.pro / admin123 to login');
      setEmail('admin@lims.pro');
      setPassword('admin123');
    } catch (error) {
      if (error.response?.data?.message === 'Data already seeded') {
        toast.info('Demo data already exists. Use admin@lims.pro / admin123');
        setEmail('admin@lims.pro');
        setPassword('admin123');
      } else {
        toast.error('Failed to seed data');
      }
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left side - Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center">
              <TestTube className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 font-heading">LIMS.Pro</h1>
              <p className="text-sm text-slate-500">Laboratory Information System</p>
            </div>
          </div>

          {/* Form */}
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-slate-900 font-heading">Welcome back</h2>
              <p className="text-slate-500 mt-1">Sign in to your account to continue</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="bg-slate-50 border-slate-200 focus:bg-white"
                  required
                  data-testid="email-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="bg-slate-50 border-slate-200 focus:bg-white pr-10"
                    required
                    data-testid="password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <Button 
                type="submit" 
                className="w-full bg-indigo-600 hover:bg-indigo-700 active:scale-95 transition-all"
                disabled={loading}
                data-testid="login-submit-btn"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign in'
                )}
              </Button>
            </form>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-slate-200" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-slate-500">Demo Access</span>
              </div>
            </div>

            <Button 
              variant="outline" 
              className="w-full"
              onClick={handleSeedData}
              disabled={seeding}
              data-testid="seed-data-btn"
            >
              {seeding ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creating demo data...
                </>
              ) : (
                'Setup Demo Data'
              )}
            </Button>

            <div className="text-xs text-slate-500 text-center space-y-1">
              <p>Demo credentials after setup:</p>
              <p className="font-mono">admin@lims.pro / admin123</p>
              <p className="font-mono">technician@lims.pro / password123</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - Hero image */}
      <div 
        className="hidden lg:block lg:w-1/2 relative bg-cover bg-center"
        style={{ backgroundImage: 'url(https://images.pexels.com/photos/4031415/pexels-photo-4031415.jpeg)' }}
      >
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-600/90 to-violet-600/80" />
        <div className="absolute inset-0 flex items-center justify-center p-12">
          <div className="text-white text-center max-w-lg">
            <h2 className="text-4xl font-bold font-heading mb-4">
              Streamline Your Lab Operations
            </h2>
            <p className="text-lg text-white/80">
              Manage patients, samples, tests, and reports with our comprehensive laboratory information management system.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
