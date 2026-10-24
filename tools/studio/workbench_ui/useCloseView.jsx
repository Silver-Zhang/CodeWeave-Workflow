import {useEffect,useRef} from 'react';

// One visible layer per Escape; closing a view never sends a process control call.
export function useCloseView(layers){
 const previous=useRef(new Map()),openers=useRef(new Map()),current=useRef(layers);current.current=layers;
 useEffect(()=>{const old=previous.current;for(const [key,active] of layers){
  if(active&&!old.get(key))openers.current.set(key,document.activeElement);
  if(!active&&old.get(key)){const target=openers.current.get(key);requestAnimationFrame(()=>{if(target?.isConnected)target.focus()});openers.current.delete(key)}
 }previous.current=new Map(layers.map(([key,active])=>[key,active]));});
 useEffect(()=>{const handler=e=>{if(e.key!=='Escape')return;const layer=[...current.current].reverse().find(x=>x[1]);if(!layer)return;e.preventDefault();e.stopImmediatePropagation();layer[2]()};window.addEventListener('keydown',handler,true);return()=>window.removeEventListener('keydown',handler,true)},[]);
}
