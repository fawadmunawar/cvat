// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import './styles.scss';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Col, Row } from 'antd/lib/grid';
import Result from 'antd/lib/result';
import Empty from 'antd/lib/empty';
import { Button } from 'antd/lib/button';
import Badge from 'antd/lib/badge';
import { Spin } from 'antd/lib/spin';
import { Bar } from 'react-chartjs-2';
import {
    BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Title, Tooltip,
} from 'chart.js';

import { Task, getCore } from 'cvat-core-wrapper';
import GoBackButton from 'components/common/go-back-button';
import CVATLoadingSpinner from 'components/common/loading-spinner';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const core = getCore();

interface ClassCount {
    label: string;
    count: number;
    by_type: Record<string, number>;
}

interface CountsResponse {
    task_id: number;
    counts: ClassCount[];
}

const TYPE_COLORS: Record<string, string> = {
    rectangle: '#1890ff',
    polygon: '#52c41a',
    polyline: '#faad14',
    points: '#eb2f96',
    ellipse: '#722ed1',
    cuboid: '#13c2c2',
    mask: '#f5222d',
    skeleton: '#a0d911',
    track: '#595959',
};

type ConnectionState = 'connecting' | 'live' | 'reconnecting';

const WS_PORT = 8090;
const RECONNECT_BACKOFF_MAX_MS = 30000;

function useAnnotationUpdates(taskId: number, onUpdate: () => void): ConnectionState {
    const [state, setState] = useState<ConnectionState>('connecting');
    const onUpdateRef = useRef(onUpdate);
    onUpdateRef.current = onUpdate;

    useEffect(() => {
        let disposed = false;
        let socket: WebSocket | null = null;
        let retryTimer: number | null = null;
        let retryDelay = 1000;

        const connect = (): void => {
            if (disposed) return;
            setState('connecting');

            const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
            socket = new WebSocket(`${scheme}://${window.location.hostname}:${WS_PORT}/ws/${taskId}`);

            socket.onopen = (): void => {
                retryDelay = 1000;
                setState('live');
                // Re-fetch right after (re)connecting: updates may have been
                // missed while the socket was down.
                onUpdateRef.current();
            };
            socket.onmessage = (): void => {
                onUpdateRef.current();
            };
            socket.onclose = (): void => {
                if (disposed) return;
                setState('reconnecting');
                retryTimer = window.setTimeout(connect, retryDelay);
                retryDelay = Math.min(retryDelay * 2, RECONNECT_BACKOFF_MAX_MS);
            };
        };

        connect();

        return (): void => {
            disposed = true;
            if (retryTimer !== null) window.clearTimeout(retryTimer);
            if (socket) socket.close();
        };
    }, [taskId]);

    return state;
}

function AnnotationCountsPage(): JSX.Element {
    const { tid } = useParams<{ tid: string }>();
    const taskId = Number.parseInt(tid, 10);

    const [task, setTask] = useState<Task | null>(null);
    const [counts, setCounts] = useState<ClassCount[] | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    const loadCounts = useCallback(async (): Promise<void> => {
        try {
            const response = await fetch(`/api/test/tasks/${taskId}/annotation-count`, {
                credentials: 'same-origin',
            });
            if (response.status === 401 || response.status === 403) {
                setError('You are not allowed to view this task.');
                return;
            }
            if (!response.ok) {
                setError(`The server answered with status ${response.status}.`);
                return;
            }
            const data = await response.json() as CountsResponse;
            setCounts(data.counts);
            setError(null);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Network error');
        } finally {
            setLoading(false);
        }
    }, [taskId]);

    useEffect(() => {
        let mounted = true;
        core.tasks.get({ id: taskId }).then(([taskInstance]) => {
            if (mounted) setTask(taskInstance);
        }).catch(() => {
            if (mounted) setError('Could not receive the requested task from the server.');
        });
        return (): void => { mounted = false; };
    }, [taskId]);

    useEffect(() => {
        void loadCounts();
    }, [loadCounts]);

    const connectionState = useAnnotationUpdates(taskId, () => {
        void loadCounts();
    });

    const typeOrder = React.useMemo(() => {
        if (!counts) return [];
        const types = new Set<string>();
        counts.forEach((entry) => Object.keys(entry.by_type).forEach((t) => types.add(t)));
        return Array.from(types);
    }, [counts]);

    const chartData = React.useMemo(() => {
        if (!counts) return null;
        return {
            labels: counts.map((entry) => entry.label),
            datasets: typeOrder.map((type) => ({
                label: type,
                data: counts.map((entry) => entry.by_type[type] ?? 0),
                backgroundColor: TYPE_COLORS[type] ?? '#8c8c8c',
                stack: 'counts',
            })),
        };
    }, [counts, typeOrder]);

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: { stacked: true, title: { display: true, text: 'Class' } },
            y: { stacked: true, beginAtZero: true, title: { display: true, text: 'Annotations' }, ticks: { precision: 0 } },
        },
    };

    const connectionBadge = (() => {
        switch (connectionState) {
            case 'live': return <Badge status='success' text='Live updates' />;
            case 'reconnecting': return <Badge status='warning' text='Reconnecting…' />;
            default: return <Badge status='processing' text='Connecting…' />;
        }
    })();

    let content: JSX.Element;
    if (error) {
        content = (
            <Result
                status='error'
                title='Could not load annotation counts'
                subTitle={error}
                extra={<Button type='primary' onClick={(): void => { void loadCounts(); }}>Retry</Button>}
            />
        );
    } else if (loading || !counts) {
        content = <CVATLoadingSpinner />;
    } else if (counts.length === 0) {
        content = <Empty description='No annotations yet for this task' />;
    } else {
        content = (
            <div className='cvat-annotation-counts-chart'>
                <Bar data={chartData} options={chartOptions} />
            </div>
        );
    }

    return (
        <div className='cvat-annotation-counts-page'>
            <Row justify='center'>
                <Col span={22} xl={18} xxl={14} className='cvat-annotation-counts-header'>
                    <GoBackButton />
                    <h2>
                        Annotation counts
                        {task && <span className='cvat-annotation-counts-task-name'> — {task.name}</span>}
                        {!loading && !error && <span className='cvat-annotation-counts-badge'>{connectionBadge}</span>}
                    </h2>
                </Col>
            </Row>
            <Row justify='center'>
                <Col span={22} xl={18} xxl={14} className='cvat-annotation-counts-content'>
                    {content}
                </Col>
            </Row>
        </div>
    );
}

export default React.memo(AnnotationCountsPage);
