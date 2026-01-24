import { useState, useEffect, useCallback } from 'react';
import { Box, Grid, Alert, Button, Typography, Skeleton } from '@mui/material';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper } from '@mui/material';
import { getLlmByAgentType, getLlmByModel } from '../../../api/costs';
import type { LlmByAgentTypeResponse, LlmByModelResponse } from '../../../api/types';
import { MetricCard } from '../components/MetricCard';

interface LlmTabProps {
  startDate: string;
  endDate: string;
}

export function LlmTab({ startDate, endDate }: LlmTabProps): JSX.Element {
  const [agentData, setAgentData] = useState<LlmByAgentTypeResponse | null>(null);
  const [modelData, setModelData] = useState<LlmByModelResponse | null>(null);
  const [loadingAgent, setLoadingAgent] = useState(true);
  const [loadingModel, setLoadingModel] = useState(true);
  const [errorAgent, setErrorAgent] = useState<string | null>(null);
  const [errorModel, setErrorModel] = useState<string | null>(null);

  const fetchAgentData = useCallback(async () => {
    setLoadingAgent(true);
    setErrorAgent(null);
    try {
      const data = await getLlmByAgentType({ start_date: startDate, end_date: endDate });
      setAgentData(data);
    } catch (err) {
      setErrorAgent(err instanceof Error ? err.message : 'Failed to load agent type data');
    } finally {
      setLoadingAgent(false);
    }
  }, [startDate, endDate]);

  const fetchModelData = useCallback(async () => {
    setLoadingModel(true);
    setErrorModel(null);
    try {
      const data = await getLlmByModel({ start_date: startDate, end_date: endDate });
      setModelData(data);
    } catch (err) {
      setErrorModel(err instanceof Error ? err.message : 'Failed to load model data');
    } finally {
      setLoadingModel(false);
    }
  }, [startDate, endDate]);

  useEffect(() => {
    fetchAgentData();
    fetchModelData();
  }, [fetchAgentData, fetchModelData]);

  const totalCost = agentData?.total_llm_cost_usd ?? modelData?.total_llm_cost_usd ?? '0';
  const totalRequests = agentData?.agent_costs.reduce((sum, a) => sum + a.request_count, 0) ?? 0;
  const avgCostPerReq = totalRequests > 0 ? parseFloat(totalCost) / totalRequests : 0;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Summary Cards */}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <MetricCard
            label="LLM Total"
            value={`$${parseFloat(totalCost).toFixed(2)}`}
            loading={loadingAgent && loadingModel}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <MetricCard
            label="Requests"
            value={totalRequests.toLocaleString()}
            loading={loadingAgent}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <MetricCard
            label="Avg Cost/Request"
            value={`$${avgCostPerReq.toFixed(3)}`}
            loading={loadingAgent}
          />
        </Grid>
      </Grid>

      {/* Agent Type Table */}
      <Box>
        <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
          Cost by Agent Type
        </Typography>
        {errorAgent ? (
          <Alert severity="error" action={<Button size="small" onClick={fetchAgentData}>Retry</Button>}>
            {errorAgent}
          </Alert>
        ) : loadingAgent ? (
          <Skeleton variant="rectangular" height={200} />
        ) : (
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Agent Type</TableCell>
                  <TableCell align="right">Cost</TableCell>
                  <TableCell align="right">Requests</TableCell>
                  <TableCell align="right">Tokens In</TableCell>
                  <TableCell align="right">Tokens Out</TableCell>
                  <TableCell align="right">%</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {agentData?.agent_costs.map((row) => (
                  <TableRow key={row.agent_type}>
                    <TableCell>{row.agent_type}</TableCell>
                    <TableCell align="right">${parseFloat(row.cost_usd).toFixed(2)}</TableCell>
                    <TableCell align="right">{row.request_count.toLocaleString()}</TableCell>
                    <TableCell align="right">{row.tokens_in.toLocaleString()}</TableCell>
                    <TableCell align="right">{row.tokens_out.toLocaleString()}</TableCell>
                    <TableCell align="right">{row.percentage.toFixed(0)}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Box>

      {/* Model Table */}
      <Box>
        <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
          Cost by Model
        </Typography>
        {errorModel ? (
          <Alert severity="error" action={<Button size="small" onClick={fetchModelData}>Retry</Button>}>
            {errorModel}
          </Alert>
        ) : loadingModel ? (
          <Skeleton variant="rectangular" height={200} />
        ) : (
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Model</TableCell>
                  <TableCell align="right">Cost</TableCell>
                  <TableCell align="right">Requests</TableCell>
                  <TableCell align="right">Tokens In</TableCell>
                  <TableCell align="right">Tokens Out</TableCell>
                  <TableCell align="right">%</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {modelData?.model_costs.map((row) => (
                  <TableRow key={row.model}>
                    <TableCell>{row.model}</TableCell>
                    <TableCell align="right">${parseFloat(row.cost_usd).toFixed(2)}</TableCell>
                    <TableCell align="right">{row.request_count.toLocaleString()}</TableCell>
                    <TableCell align="right">{row.tokens_in.toLocaleString()}</TableCell>
                    <TableCell align="right">{row.tokens_out.toLocaleString()}</TableCell>
                    <TableCell align="right">{row.percentage.toFixed(0)}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Box>
    </Box>
  );
}
