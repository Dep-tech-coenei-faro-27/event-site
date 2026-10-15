import { Component, type ErrorInfo, type ReactNode } from 'react';
import ServerError from '../pages/ServerError';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Quando muda (por exemplo o caminho), o erro é limpo e as páginas voltam a ser desenhadas. */
  resetKey?: string;
  /** Último recurso à volta de toda a aplicação: ecrã próprio e «Tentar novamente» recarrega. */
  standalone?: boolean;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Apanha erros lançados ao desenhar os filhos e mostra o ecrã de erro em vez de deixar o
 * site em branco. Não apanha erros de eventos nem de pedidos (esses tratam-se onde ocorrem).
 */
export default class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Só o erro e a árvore de componentes: nunca dados da pessoa.
    console.error('Erro ao desenhar a página:', error, info.componentStack);
  }

  componentDidUpdate(previous: ErrorBoundaryProps) {
    if (this.state.error && previous.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  private retry = () => {
    if (this.props.standalone) {
      window.location.reload();
      return;
    }
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      return <ServerError onRetry={this.retry} standalone={this.props.standalone} />;
    }
    return this.props.children;
  }
}
