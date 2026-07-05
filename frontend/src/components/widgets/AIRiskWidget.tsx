"use client";

import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface RiskData {
  category: string;
  count: number;
  color: string;
}

interface AIRiskWidgetProps {
  data: RiskData[];
}

export function AIRiskWidget({ data }: AIRiskWidgetProps) {
  // Filter out zero counts
  const chartData = data.filter(d => d.count > 0);

  return (
    <div className="h-full flex flex-col min-h-[200px]">
      {chartData.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-slate-400">
          No risk data available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={80}
              paddingAngle={5}
              dataKey="count"
              nameKey="category"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip 
              contentStyle={{ borderRadius: '12px', border: '1px solid #E2E8F0', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
            />
            <Legend verticalAlign="bottom" height={36} iconType="circle" />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
