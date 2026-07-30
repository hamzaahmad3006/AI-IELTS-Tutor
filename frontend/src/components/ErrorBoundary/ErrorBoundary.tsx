/**
 * Top-level crash guard.
 *
 * Without this, an exception thrown while rendering unmounts the whole tree and
 * React Native shows a blank screen in release builds — the user's only way out
 * is to force-quit. This catches it and offers a way back.
 *
 * Must be a class component: there is still no hook equivalent of
 * componentDidCatch.
 */

import React from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText } from '../AppText/AppText';
import { Button } from '../Button/Button';
import { Icon } from '../Icon/Icon';
import { SPACING } from '../../constants';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  /** Hook for a crash reporter; called with the render error. */
  onError?: (error: Error, componentStack: string) => void;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    this.props.onError?.(error, info.componentStack ?? '');
    if (__DEV__) {
      console.error('[ErrorBoundary]', error, info.componentStack);
    }
  }

  private readonly reset = (): void => {
    // Remounting the subtree is the honest recovery: whatever state caused the
    // throw is rebuilt from the store rather than patched over.
    this.setState({ error: null });
  };

  render(): React.ReactNode {
    const { error } = this.state;
    if (!error) {
      return this.props.children;
    }

    return (
      <View style={styles.wrap} testID="error-boundary-fallback">
        <Icon name="info" size={48} color="error" />
        <AppText variant="headlineMd" align="center" style={styles.title}>
          Something broke
        </AppText>
        <AppText variant="bodyMd" color="textSecondary" align="center">
          The screen failed to load. Your progress is saved — try again.
        </AppText>
        {__DEV__ ? (
          <AppText variant="labelSm" color="textMuted" style={styles.detail}>
            {error.message}
          </AppText>
        ) : null}
        <Button
          title="Try again"
          onPress={this.reset}
          fullWidth={false}
          style={styles.action}
        />
      </View>
    );
  }
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: SPACING.lg,
  },
  title: { marginTop: SPACING.md, marginBottom: SPACING.xs },
  detail: { marginTop: SPACING.md, textAlign: 'center' },
  action: { marginTop: SPACING.lg },
});
