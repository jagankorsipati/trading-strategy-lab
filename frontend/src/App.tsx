import { Layout } from './components/Layout'
import { usePath } from './components/Router'
import { BacktestsPage } from './pages/BacktestsPage'
import { ComparisonPage } from './pages/ComparisonPage'
import { ExecutionPage } from './pages/ExecutionPage'
import { OverviewPage } from './pages/OverviewPage'
import { PerformancePage } from './pages/PerformancePage'
import { ReportsPage } from './pages/ReportsPage'
import { StrategiesPage } from './pages/StrategiesPage'
import { TradesPage } from './pages/TradesPage'
import { WalkForwardPage } from './pages/WalkForwardPage'
import type { ComponentType } from 'react'
const pages:Record<string,ComponentType>={'/':OverviewPage,'/strategies':StrategiesPage,'/backtests':BacktestsPage,'/performance':PerformancePage,'/trades':TradesPage,'/walk-forward':WalkForwardPage,'/execution':ExecutionPage,'/comparison':ComparisonPage,'/reports':ReportsPage}
export default function App(){const path=usePath();const Page=pages[path]??OverviewPage;return <Layout path={path}><Page/></Layout>}
