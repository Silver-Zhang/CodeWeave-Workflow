import React from 'react';
import {BaseEdge,getSmoothStepPath,EdgeLabelRenderer} from '@xyflow/react';
export function HandoffEdge(props){
 const [path,x,y]=getSmoothStepPath({...props,borderRadius:20,offset:28});
 const event=props.data?.pulse;
 return <><BaseEdge id={props.id} path={path} style={props.style} markerEnd={props.markerEnd} interactionWidth={26}/>{event&&<path key={event.run+':'+event.seq} d={path} fill="none" className="handoff-pulse" data-event={event.seq} data-run={event.run} aria-hidden="true"/>}{props.label&&<EdgeLabelRenderer><span className="edge-label nodrag nopan" style={{transform:`translate(-50%, -50%) translate(${x}px,${y}px)`}}>{props.label}</span></EdgeLabelRenderer>}</>;
}
