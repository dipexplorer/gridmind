"use client";

import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, BarChart2, ShieldAlert, Cpu, 
  Activity, Play, CheckCircle2, AlertTriangle, 
  HelpCircle, RefreshCw 
} from 'lucide-react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, 
  Tooltip, Legend, ResponsiveContainer, BarChart, Bar 
} from 'recharts';
import { apiClient } from '@/lib/api';

interface ModelMetric {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  roc_auc: number;
  cv_mean_f1: number;
  confusion_matrix: number[][];
}

interface BenchmarkData {
  summary: {
    best_model: string;
    best_roc_auc: number;
    total_samples: number;
  };
  models: Record<string, ModelMetric>;
  roc_data: Record<string, Record<string, { fpr: number[]; tpr: number[]; auc: number }>>;
}

interface DeepLearningData {
  lstm: {
    model: string;
    final_val_loss: number;
    epochs_trained: number;
  };
  cnn1d: {
    model: string;
    best_val_accuracy: number;
    classes: string[];
  };
}

interface RLAgentData {
  model: string;
  algorithm: string;
  results: {
    success_rate: number;
    avg_reward_last_500_episodes: number;
  };
}

export default function MLAnalyticsPage() {
  const [activeTab, setActiveTab] = useState<'benchmark' | 'dl' | 'rl'>('benchmark');
  const [benchmark, setBenchmark] = useState<BenchmarkData | null>(null);
  const [dlData, setDlData] = useState<DeepLearningData | null>(null);
  const [rlData, setRlData] = useState<RLAgentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [trainingStatus, setTrainingStatus] = useState<string | null>(null);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [benchRes, dlRes, rlRes] = await Promise.allSettled([
        apiClient.get('/ml/benchmark'),
        apiClient.get('/ml/deep-learning'),
        apiClient.get('/ml/rl-agent')
      ]);

      if (benchRes.status === 'fulfilled') setBenchmark(benchRes.value.data);
      if (dlRes.status === 'fulfilled') setDlData(dlRes.value.data);
      if (rlRes.status === 'fulfilled') setRlData(rlRes.value.data);
    } catch (err) {
      console.error("Error fetching ML analytics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  const triggerTraining = async (type: 'benchmark' | 'deep-learning' | 'rl-agent') => {
    setTrainingStatus(`Triggered ${type} training...`);
    try {
      const endpoint = `/ml/run-${type}`;
      const response = await apiClient.post(endpoint);
      setTrainingStatus(response.data.message);
      setTimeout(() => setTrainingStatus(null), 8000);
    } catch (err: any) {
      setTrainingStatus(`Failed to trigger training: ${err.message}`);
    }
  };

  // Convert ROC curve coordinate arrays to Recharts format
  const getRocChartData = () => {
    if (!benchmark?.roc_data) return [];
    const modelNames = Object.keys(benchmark.roc_data);
    const chartData: any[] = [];
    
    // Generate 20 intervals from 0 to 1 for FPR
    for (let step = 0; step <= 20; step++) {
      const fprVal = step / 20;
      const dataPoint: any = { fpr: fprVal };
      
      modelNames.forEach(modelName => {
        // Find the closest TPR for this FPR value
        const curves = benchmark.roc_data[modelName];
        const criticalCurve = curves["CRITICAL"];
        if (criticalCurve) {
          const idx = criticalCurve.fpr.findIndex(val => val >= fprVal);
          dataPoint[modelName] = idx !== -1 ? criticalCurve.tpr[idx] : 1.0;
        }
      });
      chartData.push(dataPoint);
    }
    return chartData;
  };

  // Simulated LSTM Forecasting data for viz
  const lstmForecastData = [
    { hour: '-12h', actualLoad: 45, actualTemp: 52 },
    { hour: '-9h', actualLoad: 50, actualTemp: 54 },
    { hour: '-6h', actualLoad: 68, actualTemp: 60 },
    { hour: '-3h', actualLoad: 85, actualTemp: 72 },
    { hour: 'Now', actualLoad: 92, actualTemp: 82, predLoad: 92, predTemp: 82 },
    { hour: '+3h', predLoad: 98, predTemp: 85 },
    { hour: '+6h', predLoad: 110, predTemp: 92 },
    { hour: '+9h', predLoad: 80, predTemp: 84 },
    { hour: '+12h', predLoad: 65, predTemp: 75 },
    { hour: '+15h', predLoad: 50, predTemp: 68 },
    { hour: '+18h', predLoad: 42, predTemp: 62 },
    { hour: '+21h', predLoad: 55, predTemp: 60 },
    { hour: '+24h', predLoad: 62, predTemp: 63 }
  ];

  return (
    <div className="min-h-screen bg-[#07090E] text-slate-100 p-8 pl-72">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800/60 mb-8">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
            AI Analytics & Academic Suite
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Validate model accuracy metrics, deep learning architectures, and RL prescriptive controls.
          </p>
        </div>

        <div className="flex items-center space-x-3 mt-4 md:mt-0">
          <button 
            onClick={fetchAllData}
            className="p-2.5 rounded-xl border border-slate-800 bg-[#0B1121] hover:bg-slate-800/80 transition-colors text-slate-400 hover:text-slate-200"
          >
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          </button>
          
          <div className="dropdown relative group">
            <button className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-semibold text-sm transition-all shadow-lg shadow-indigo-500/20">
              <Play size={15} className="fill-white" />
              <span>Train Pipelines</span>
            </button>
            
            <div className="absolute right-0 top-12 w-56 rounded-xl border border-slate-800 bg-[#0F172A] p-2 shadow-2xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
              <button 
                onClick={() => triggerTraining('benchmark')}
                className="w-full text-left px-3 py-2 rounded-lg text-xs hover:bg-slate-800 transition-colors"
              >
                Train 5-Model Benchmark
              </button>
              <button 
                onClick={() => triggerTraining('deep-learning')}
                className="w-full text-left px-3 py-2 rounded-lg text-xs hover:bg-slate-800 transition-colors"
              >
                Train PyTorch LSTM & CNN
              </button>
              <button 
                onClick={() => triggerTraining('rl-agent')}
                className="w-full text-left px-3 py-2 rounded-lg text-xs hover:bg-slate-800 transition-colors"
              >
                Train RL Balancer Agent
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Notification banner */}
      {trainingStatus && (
        <div className="mb-6 p-4 rounded-xl border border-indigo-500/30 bg-indigo-950/20 text-indigo-300 flex items-center space-x-3 text-sm animate-pulse">
          <Activity size={18} />
          <span>{trainingStatus}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-800 mb-8 space-x-8">
        <button
          onClick={() => setActiveTab('benchmark')}
          className={`pb-4 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'benchmark' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Model Benchmarks
        </button>
        <button
          onClick={() => setActiveTab('dl')}
          className={`pb-4 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'dl' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Deep Learning (LSTM & CNN)
        </button>
        <button
          onClick={() => setActiveTab('rl')}
          className={`pb-4 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'rl' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          RL Load Balancer
        </button>
      </div>

      {/* Tab Contents */}
      {loading ? (
        <div className="flex flex-col items-center justify-center h-64 space-y-3">
          <RefreshCw className="animate-spin text-indigo-500" size={32} />
          <p className="text-slate-400 text-sm">Loading ML Suite analytics data...</p>
        </div>
      ) : (
        <>
          {activeTab === 'benchmark' && benchmark && (
            <div className="space-y-8">
              {/* Highlight cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-6 rounded-2xl border border-slate-800 bg-[#0B1121] flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
                    <CheckCircle2 size={24} />
                  </div>
                  <div>
                    <h3 className="text-xs text-slate-400 uppercase tracking-widest font-semibold">Best Model</h3>
                    <p className="text-xl font-bold text-white mt-1">{benchmark.summary.best_model}</p>
                  </div>
                </div>

                <div className="p-6 rounded-2xl border border-slate-800 bg-[#0B1121] flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                    <TrendingUp size={24} />
                  </div>
                  <div>
                    <h3 className="text-xs text-slate-400 uppercase tracking-widest font-semibold">Highest ROC-AUC</h3>
                    <p className="text-xl font-bold text-white mt-1">{benchmark.summary.best_roc_auc.toFixed(4)}</p>
                  </div>
                </div>

                <div className="p-6 rounded-2xl border border-slate-800 bg-[#0B1121] flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center">
                    <Activity size={24} />
                  </div>
                  <div>
                    <h3 className="text-xs text-slate-400 uppercase tracking-widest font-semibold">Test Sample Count</h3>
                    <p className="text-xl font-bold text-white mt-1">{benchmark.summary.total_samples}</p>
                  </div>
                </div>
              </div>

              {/* Main table & ROC Curve */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Table */}
                <div className="p-6 rounded-2xl border border-slate-800 bg-[#0B1121]">
                  <h3 className="text-lg font-bold text-white mb-4">Classifiers Performance Metrics</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                          <th className="py-3">Model</th>
                          <th className="py-3 text-right">Accuracy</th>
                          <th className="py-3 text-right">F1-Score</th>
                          <th className="py-3 text-right">ROC-AUC</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {Object.entries(benchmark.models).map(([name, metrics]) => (
                          <tr key={name} className="hover:bg-slate-800/20 transition-colors">
                            <td className="py-4 font-semibold text-white">{name}</td>
                            <td className="py-4 text-right text-slate-300">{(metrics.accuracy * 100).toFixed(1)}%</td>
                            <td className="py-4 text-right text-slate-300">{metrics.f1_score.toFixed(4)}</td>
                            <td className="py-4 text-right text-indigo-400 font-semibold">{metrics.roc_auc.toFixed(4)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* ROC Curve chart */}
                <div className="p-6 rounded-2xl border border-slate-800 bg-[#0B1121] flex flex-col">
                  <h3 className="text-lg font-bold text-white mb-2">ROC Curves (Critical Anomaly Class)</h3>
                  <p className="text-slate-400 text-xs mb-6">Shows Sensitivity vs 1-Specificity across classifiers.</p>
                  
                  <div className="flex-1 min-h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={getRocChartData()} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                        <XAxis dataKey="fpr" label={{ value: 'False Positive Rate', position: 'insideBottom', offset: -5 }} stroke="#64748B" />
                        <YAxis label={{ value: 'True Positive Rate', angle: -90, position: 'insideLeft' }} stroke="#64748B" />
                        <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155' }} />
                        <Legend />
                        {Object.keys(benchmark.models).map((modelName, idx) => {
                          const colors = ["#6366F1", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6"];
                          return (
                            <Line 
                              key={modelName}
                              type="monotone"
                              dataKey={modelName}
                              stroke={colors[idx % colors.length]}
                              strokeWidth={2}
                              dot={false}
                            />
                          );
                        })}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'dl' && dlData && (
            <div className="space-y-8">
              {/* Architecture Info cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* LSTM card */}
                <div className="p-6 rounded-2xl border border-slate-800 bg-[#0B1121] space-y-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                      <Cpu size={20} />
                    </div>
                    <div>
                      <h3 className="text-md font-bold text-white">LSTM Time-Series Forecaster</h3>
                      <p className="text-slate-400 text-xs">2-layer Stacked LSTM + Dense Decoder Head</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm border-t border-slate-800 pt-4">
                    <div>
                      <span className="text-slate-400 block text-xs">Validation Loss (MSE)</span>
                      <strong className="text-white text-lg font-bold">{dlData.lstm.final_val_loss.toFixed(6)}</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-xs">Epochs Trained</span>
                      <strong className="text-white text-lg font-bold">{dlData.lstm.epochs_trained}</strong>
                    </div>
                  </div>
                </div>

                {/* CNN card */}
                <div className="p-6 rounded-2xl border border-slate-800 bg-[#0B1121] space-y-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center">
                      <BarChart2 size={20} />
                    </div>
                    <div>
                      <h3 className="text-md font-bold text-white">1D-CNN Waveform Classifier</h3>
                      <p className="text-slate-400 text-xs">3x Conv1d Blocks + Fully Connected Classifier</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm border-t border-slate-800 pt-4">
                    <div>
                      <span className="text-slate-400 block text-xs">Accuracy (Fault Prediction)</span>
                      <strong className="text-white text-lg font-bold">{(dlData.cnn1d.best_val_accuracy * 100).toFixed(1)}%</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-xs">Classes Classified</span>
                      <strong className="text-white text-lg font-bold">{dlData.cnn1d.classes.length} Types</strong>
                    </div>
                  </div>
                </div>
              </div>

              {/* Forecasting chart */}
              <div className="p-6 rounded-2xl border border-slate-800 bg-[#0B1121]">
                <h3 className="text-lg font-bold text-white mb-2">24h Load & Temperature Future Forecasting</h3>
                <p className="text-slate-400 text-xs mb-6">LSTM prediction (dotted lines) versus actual recorded past parameters.</p>
                
                <div className="h-[350px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={lstmForecastData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                      <XAxis dataKey="hour" stroke="#64748B" />
                      <YAxis stroke="#64748B" />
                      <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155' }} />
                      <Legend />
                      <Line type="monotone" dataKey="actualLoad" name="Actual Load (%)" stroke="#6366F1" strokeWidth={3} dot={false} />
                      <Line type="monotone" dataKey="predLoad" name="Predicted Load (%)" stroke="#6366F1" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                      <Line type="monotone" dataKey="actualTemp" name="Actual Temp (°C)" stroke="#EC4899" strokeWidth={3} dot={false} />
                      <Line type="monotone" dataKey="predTemp" name="Predicted Temp (°C)" stroke="#EC4899" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'rl' && rlData && (
            <div className="space-y-8">
              {/* RL stats cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="p-6 rounded-2xl border border-slate-800 bg-[#0B1121] space-y-4">
                  <h3 className="text-md font-bold text-white mb-2">Prescriptive Agent Metrics</h3>
                  <div className="grid grid-cols-2 gap-4 border-t border-slate-800 pt-4">
                    <div>
                      <span className="text-slate-400 block text-xs">Load Balance Success Rate</span>
                      <strong className="text-white text-lg font-bold">{(rlData.results.success_rate * 100).toFixed(1)}%</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-xs">Average Policy Reward</span>
                      <strong className="text-white text-lg font-bold">{rlData.results.avg_reward_last_500_episodes.toFixed(2)}</strong>
                    </div>
                  </div>
                </div>

                <div className="p-6 rounded-2xl border border-slate-800 bg-[#0B1121] flex flex-col justify-center space-y-2">
                  <h3 className="text-md font-bold text-white">Q-Learning Strategy</h3>
                  <p className="text-slate-400 text-xs leading-relaxed">
                    When Transformer A reaches a critical temperature bin (&gt;80°C) and load bin (&gt;80%), the RL Agent consults the Q-table to trigger the optimal action (e.g. transfer 30% load to Transformer B) maximizing reward and avoiding secondary grid blackouts.
                  </p>
                </div>
              </div>

              {/* Simulation visual widget */}
              <div className="p-6 rounded-2xl border border-slate-800 bg-[#0B1121] space-y-6">
                <h3 className="text-lg font-bold text-white">Load Balancing Simulation</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
                  <div className="border border-slate-800 bg-[#07090E] p-6 rounded-xl space-y-4 text-center">
                    <h4 className="text-sm font-semibold text-slate-300">Transformer A (Critical)</h4>
                    <div className="relative w-full bg-slate-800 rounded-full h-4 overflow-hidden">
                      <div className="bg-red-500 h-full w-[90%]" />
                    </div>
                    <div className="flex justify-between text-xs text-slate-400">
                      <span>Load: 92%</span>
                      <span>Temp: 84°C</span>
                    </div>
                  </div>

                  <div className="border border-slate-800 bg-[#07090E] p-6 rounded-xl space-y-4 text-center">
                    <h4 className="text-sm font-semibold text-slate-300">Transformer B (Healthy)</h4>
                    <div className="relative w-full bg-slate-800 rounded-full h-4 overflow-hidden">
                      <div className="bg-emerald-500 h-full w-[45%]" />
                    </div>
                    <div className="flex justify-between text-xs text-slate-400">
                      <span>Load: 45%</span>
                      <span>Temp: 52°C</span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col items-center justify-center p-4 border border-indigo-500/20 bg-indigo-950/10 rounded-xl">
                  <span className="text-xs text-indigo-400 uppercase tracking-widest font-semibold mb-2">Prescriptive Recommendation</span>
                  <div className="flex items-center space-x-3 text-sm text-indigo-300 font-bold">
                    <ShieldAlert size={18} />
                    <span>RL Agent recommends: Shift 30% Load from A to B</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
