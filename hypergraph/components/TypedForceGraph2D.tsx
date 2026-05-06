"use client";

import dynamic from "next/dynamic";
import { forwardRef, useImperativeHandle, useRef } from "react";
import type { ReactElement, MutableRefObject } from "react";
import type {
  ForceGraphMethods,
  ForceGraphProps,
  LinkObject,
  NodeObject,
} from "react-force-graph-2d";

type RawNode = NodeObject;
type RawLink = LinkObject;

type ForceGraph2DComponent = (
  props: ForceGraphProps & {
    ref?: MutableRefObject<ForceGraphMethods<RawNode, RawLink> | undefined>;
  }
) => ReactElement;

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
}) as unknown as ForceGraph2DComponent;

interface GraphNodeLike {
  type?: unknown;
}

interface GraphLinkLike {
  source?: GraphNodeLike;
  target?: GraphNodeLike;
}

export interface GraphForceTuning {
  chargeStrength: number;
  chargeDistanceMax: number;
  mocDistance: number;
  defaultDistance: number;
}

export interface TypedForceGraphHandle {
  zoomToFit: (durationMs?: number, padding?: number) => void;
  applyForces: (tuning: GraphForceTuning) => void;
}

type TypedForceGraphProps = Omit<ForceGraphProps, "ref">;

const TypedForceGraph2D = forwardRef<TypedForceGraphHandle, TypedForceGraphProps>(
  function TypedForceGraph2D(props, ref) {
    const innerRef = useRef<ForceGraphMethods<RawNode, RawLink> | undefined>(
      undefined
    );

    useImperativeHandle(ref, () => ({
      zoomToFit(durationMs, padding) {
        innerRef.current?.zoomToFit(durationMs, padding);
      },
      applyForces(tuning) {
        const chargeForce = innerRef.current?.d3Force("charge");
        if (chargeForce) {
          const maybeCharge = chargeForce as {
            strength?: (value: number) => void;
            distanceMax?: (value: number) => void;
          };
          maybeCharge.strength?.(tuning.chargeStrength);
          maybeCharge.distanceMax?.(tuning.chargeDistanceMax);
        }

        const linkForce = innerRef.current?.d3Force("link");
        if (linkForce) {
          const maybeLink = linkForce as {
            distance?: (fn: (link: GraphLinkLike) => number) => void;
          };
          maybeLink.distance?.((link) => {
            const srcType = link.source?.type;
            const dstType = link.target?.type;
            if (srcType === "moc" || dstType === "moc") return tuning.mocDistance;
            return tuning.defaultDistance;
          });
        }
      },
    }));

    return <ForceGraph2D {...props} ref={innerRef} />;
  }
);

export default TypedForceGraph2D;
