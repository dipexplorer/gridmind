'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';
import { Zap, Loader2 } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Check if user is already logged in
    const checkSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        router.push('/');
      }
    };
    checkSession();
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      if (isLogin) {
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        if (data.session) {
          router.push('/');
        }
      } else {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
        });
        if (error) throw error;
        
        if (data.user?.identities?.length === 0) {
           setError('User already exists. Please sign in instead.');
        } else {
           setSuccess('Registration successful! You can now sign in.');
           setIsLogin(true); // Switch back to login view
        }
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background gradients */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-blue-600/20 blur-[120px]" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-cyan-600/20 blur-[120px]" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="flex justify-center">
          <div className="h-14 w-14 bg-blue-500/10 rounded-2xl border border-blue-500/20 flex items-center justify-center backdrop-blur-sm shadow-[0_0_15px_rgba(59,130,246,0.3)]">
            <Zap className="h-8 w-8 text-blue-400" />
          </div>
        </div>
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-white">
          GridMind Portal
        </h2>
        <p className="mt-2 text-center text-sm text-slate-400">
          Sign in or create an account to access the platform
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-slate-900/60 backdrop-blur-xl py-8 px-4 shadow-2xl shadow-blue-900/10 sm:rounded-2xl sm:px-10 border border-slate-800">
          
          {/* Tabs */}
          <div className="flex mb-6 border-b border-slate-800">
            <button
              onClick={() => setIsLogin(true)}
              className={`flex-1 pb-3 text-sm font-medium ${isLogin ? 'text-blue-500 border-b-2 border-blue-500' : 'text-slate-400 hover:text-slate-300'}`}
            >
              Sign In
            </button>
            <button
              onClick={() => setIsLogin(false)}
              className={`flex-1 pb-3 text-sm font-medium ${!isLogin ? 'text-blue-500 border-b-2 border-blue-500' : 'text-slate-400 hover:text-slate-300'}`}
            >
              Sign Up
            </button>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="email" className="block text-sm font-medium leading-6 text-slate-300">
                Email address
              </label>
              <div className="mt-2">
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full rounded-lg border-0 bg-slate-800/50 py-2.5 px-3.5 text-white shadow-sm ring-1 ring-inset ring-slate-700 placeholder:text-slate-500 focus:ring-2 focus:ring-inset focus:ring-blue-500 sm:text-sm sm:leading-6 backdrop-blur-sm transition-all"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium leading-6 text-slate-300">
                Password
              </label>
              <div className="mt-2">
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete={isLogin ? "current-password" : "new-password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full rounded-lg border-0 bg-slate-800/50 py-2.5 px-3.5 text-white shadow-sm ring-1 ring-inset ring-slate-700 placeholder:text-slate-500 focus:ring-2 focus:ring-inset focus:ring-blue-500 sm:text-sm sm:leading-6 backdrop-blur-sm transition-all"
                />
              </div>
            </div>

            {error && (
              <div className="rounded-md bg-red-500/10 p-4 border border-red-500/20">
                <h3 className="text-sm font-medium text-red-400">{error}</h3>
              </div>
            )}

            {success && (
              <div className="rounded-md bg-green-500/10 p-4 border border-green-500/20">
                <h3 className="text-sm font-medium text-green-400">{success}</h3>
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={loading}
                className="flex w-full justify-center items-center rounded-lg bg-blue-600 px-3 py-2.5 text-sm font-semibold leading-6 text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin -ml-1 mr-2 h-4 w-4" />
                    {isLogin ? 'Signing in...' : 'Creating account...'}
                  </>
                ) : (
                  isLogin ? 'Sign in' : 'Create account'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
