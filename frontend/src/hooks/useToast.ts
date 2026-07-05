// ─── Toast Hook ───────────────────────────────────────────────────────────────
import * as React from 'react';

const TOAST_LIMIT = 3;

type ToasterToast = {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  variant?: 'default' | 'destructive';
};

const actionTypes = {
  ADD_TOAST: 'ADD_TOAST',
  UPDATE_TOAST: 'UPDATE_TOAST',
  DISMISS_TOAST: 'DISMISS_TOAST',
  REMOVE_TOAST: 'REMOVE_TOAST',
} as const;

let count = 0;

function genId() {
  count = (count + 1) % Number.MAX_VALUE;
  return count.toString();
}

type ActionType = typeof actionTypes;

type Action =
  | { type: ActionType['ADD_TOAST']; toast: ToasterToast }
  | { type: ActionType['UPDATE_TOAST']; toast: Partial<ToasterToast> }
  | { type: ActionType['DISMISS_TOAST']; toastId?: string }
  | { type: ActionType['REMOVE_TOAST']; toastId?: string };

interface State {
  toasts: ToasterToast[];
}

export const toastState = {
  toasts: [] as ToasterToast[],
  listeners: [] as Array<(state: State) => void>,
};

function dispatch(action: Action) {
  let memoryState = { toasts: toastState.toasts };

  switch (action.type) {
    case 'ADD_TOAST':
      memoryState.toasts = [action.toast, ...memoryState.toasts].slice(0, TOAST_LIMIT);
      break;
    case 'UPDATE_TOAST':
      memoryState.toasts = memoryState.toasts.map((t) =>
        t.id === action.toast.id ? { ...t, ...action.toast } : t
      );
      break;
    case 'DISMISS_TOAST': {
      if (action.toastId) {
        memoryState.toasts = memoryState.toasts.filter((t) => t.id !== action.toastId);
      } else {
        memoryState.toasts = [];
      }
      break;
    }
  }

  toastState.toasts = memoryState.toasts;
  toastState.listeners.forEach((listener) => {
    listener(memoryState);
  });
}

export function toast(props: Omit<ToasterToast, 'id'>) {
  const id = genId();

  const update = (props: ToasterToast) =>
    dispatch({ type: 'UPDATE_TOAST', toast: { ...props, id } });

  const dismiss = () => dispatch({ type: 'DISMISS_TOAST', toastId: id });

  dispatch({
    type: 'ADD_TOAST',
    toast: {
      ...props,
      id,
    },
  });

  return {
    id,
    dismiss,
    update,
  };
}

export function useToast() {
  const [state, setState] = React.useState<State>({ toasts: toastState.toasts });

  React.useEffect(() => {
    const listener = (state: State) => setState(state);
    toastState.listeners.push(listener);
    return () => {
      const index = toastState.listeners.indexOf(listener);
      if (index > -1) {
        toastState.listeners.splice(index, 1);
      }
    };
  }, [state]);

  return {
    ...state,
    toast,
    dismiss: (toastId?: string) => dispatch({ type: 'DISMISS_TOAST', toastId }),
  };
}
